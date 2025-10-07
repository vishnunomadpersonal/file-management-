CREATE DATABASE IF NOT EXISTS filemanager;
CREATE DATABASE IF NOT EXISTS filemanager_test;

CREATE USER 'filemanager_user'@'%' IDENTIFIED WITH mysql_native_password BY 'filemanager_pass';
GRANT ALL PRIVILEGES ON filemanager.* TO 'filemanager_user'@'%';
GRANT ALL PRIVILEGES ON filemanager_test.* TO 'filemanager_user'@'%';

FLUSH PRIVILEGES;