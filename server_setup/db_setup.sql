
/* Create user */
CREATE USER 'hallondisp'@'localhost' IDENTIFIED BY 'hallondisp';
GRANT USAGE ON *.* TO 'hallondisp'@'localhost';
GRANT EXECUTE, SELECT, SHOW VIEW, ALTER, ALTER ROUTINE, CREATE, CREATE ROUTINE, CREATE TEMPORARY TABLES, CREATE VIEW, DELETE, DROP, EVENT, INDEX, INSERT, REFERENCES, TRIGGER, UPDATE, LOCK TABLES  ON `hallondisp`.* TO 'hallondisp'@'localhost' WITH GRANT OPTION;
FLUSH PRIVILEGES;
SHOW GRANTS FOR 'hallondisp'@'localhost';

/* Create database */
CREATE DATABASE `hallondisp`;

/* Create table */
CREATE TABLE `measurements` (
	`TimeStamp` TIMESTAMP NULL,
	`SensorId` VARCHAR(50) NULL DEFAULT NULL,
	`Value1` FLOAT NULL DEFAULT NULL,
	`Value2` FLOAT NULL DEFAULT NULL
) COLLATE='utf8mb4_general_ci';
