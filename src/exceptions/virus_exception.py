class VirusDetectedException(Exception):
    """Exception raised when a virus is detected in an uploaded file"""
    
    def __init__(self, message: str, virus_name: str = None, scan_result: dict = None):
        self.message = message
        self.virus_name = virus_name
        self.scan_result = scan_result or {}
        super().__init__(self.message)

class VirusScanException(Exception):
    """Exception raised when virus scanning fails"""
    
    def __init__(self, message: str, scan_result: dict = None):
        self.message = message
        self.scan_result = scan_result or {}
        super().__init__(self.message)