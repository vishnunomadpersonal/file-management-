import aiohttp
import asyncio
import logging
import hashlib
from typing import Optional, Dict, Any
from core.config import config

logger = logging.getLogger(__name__)

class VirusScanner:
    def __init__(self):
        self.clamav_url = config.CLAMAV_REST_URL
        self.enabled = config.VIRUS_SCAN_ENABLED
        
    async def scan_file(self, file_path: str) -> Dict[str, Any]:
        """
        Scan a file for viruses using ClamAV
        Returns: {
            'is_infected': bool,
            'virus_name': str or None,
            'scan_result': str,
            'scanner': str,
            'file_size': int
        }
        """
        if not self.enabled:
            logger.info("Virus scanning is disabled")
            return {
                'is_infected': False,
                'virus_name': None,
                'scan_result': 'SCAN_DISABLED',
                'scanner': 'ClamAV',
                'file_size': 0
            }
            
        try:
            # Check file size limit
            import os
            file_size = os.path.getsize(file_path)
            if file_size > config.MAX_SCAN_FILE_SIZE:
                logger.warning(f"File size {file_size} exceeds scan limit {config.MAX_SCAN_FILE_SIZE}")
                return {
                    'is_infected': None,
                    'virus_name': None,
                    'scan_result': 'FILE_TOO_LARGE',
                    'scanner': 'ClamAV',
                    'file_size': file_size,
                    'error': f'File size {file_size} exceeds maximum scan size {config.MAX_SCAN_FILE_SIZE}'
                }
            
            logger.info(f"Starting virus scan for file: {file_path} (size: {file_size} bytes)")
            
            async with aiohttp.ClientSession() as session:
                with open(file_path, 'rb') as file:
                    data = aiohttp.FormData()
                    data.add_field('file', file, filename=file_path.split('/')[-1])
                    
                    async with session.post(f"{self.clamav_url}/scan", data=data, timeout=300) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.info(f"ClamAV scan result: {result}")
                            
                            return {
                                'is_infected': result.get('is_infected', False),
                                'virus_name': result.get('virus_name'),
                                'scan_result': result.get('result', 'OK'),
                                'scanner': 'ClamAV',
                                'file_size': file_size
                            }
                        else:
                            error_text = await response.text()
                            logger.error(f"ClamAV scan failed with status {response.status}: {error_text}")
                            return self._scan_error_result(file_size, f"HTTP {response.status}: {error_text}")
                            
        except asyncio.TimeoutError:
            logger.error("ClamAV scan timed out")
            return self._scan_error_result(0, "Scan timeout")
        except aiohttp.ClientError as e:
            logger.error(f"ClamAV connection error: {str(e)}")
            return self._scan_error_result(0, f"Connection error: {str(e)}")
        except FileNotFoundError:
            logger.error(f"File not found for scanning: {file_path}")
            return self._scan_error_result(0, "File not found")
        except Exception as e:
            logger.error(f"Virus scan failed: {str(e)}")
            return self._scan_error_result(0, str(e))
    
    async def scan_file_content(self, file_content: bytes, filename: str) -> Dict[str, Any]:
        """Scan file content directly without saving to disk"""
        if not self.enabled:
            return {
                'is_infected': False,
                'virus_name': None,
                'scan_result': 'SCAN_DISABLED',
                'scanner': 'ClamAV',
                'file_size': len(file_content)
            }
            
        try:
            file_size = len(file_content)
            if file_size > config.MAX_SCAN_FILE_SIZE:
                logger.warning(f"File content size {file_size} exceeds scan limit")
                return self._scan_error_result(file_size, "File too large for scanning")
            
            logger.info(f"Starting virus scan for file content: {filename} (size: {file_size} bytes)")
            
            async with aiohttp.ClientSession() as session:
                data = aiohttp.FormData()
                data.add_field('file', file_content, filename=filename)
                
                async with session.post(f"{self.clamav_url}/scan", data=data, timeout=300) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.info(f"ClamAV scan result for {filename}: {result}")
                        
                        return {
                            'is_infected': result.get('is_infected', False),
                            'virus_name': result.get('virus_name'),
                            'scan_result': result.get('result', 'OK'),
                            'scanner': 'ClamAV',
                            'file_size': file_size
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"ClamAV scan failed: {error_text}")
                        return self._scan_error_result(file_size, error_text)
                        
        except Exception as e:
            logger.error(f"Virus scan failed for {filename}: {str(e)}")
            return self._scan_error_result(len(file_content) if file_content else 0, str(e))
    
    def _scan_error_result(self, file_size: int = 0, error_message: str = "Scanning service unavailable") -> Dict[str, Any]:
        """Return error result when scanning fails"""
        return {
            'is_infected': None,  # Unknown status
            'virus_name': None,
            'scan_result': 'SCAN_ERROR',
            'scanner': 'ClamAV',
            'file_size': file_size,
            'error': error_message
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check if ClamAV service is available"""
        if not self.enabled:
            return {'status': 'disabled', 'message': 'Virus scanning is disabled'}
            
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.clamav_url}/", timeout=10) as response:
                    if response.status == 200:
                        return {'status': 'healthy', 'message': 'ClamAV service is available'}
                    else:
                        return {'status': 'unhealthy', 'message': f'ClamAV returned status {response.status}'}
        except Exception as e:
            return {'status': 'unhealthy', 'message': f'ClamAV service unavailable: {str(e)}'}

# Singleton instance
virus_scanner = VirusScanner()