
/* Create database */
CREATE DATABASE `hallondisp`;

/* Create table */
CREATE TABLE `hallondisp`.`measurements` (`TimeStamp` TIMESTAMP(3) NULL,`SensorId` VARCHAR(50) NULL DEFAULT NULL,`Value1` FLOAT NULL DEFAULT NULL,`Value2` FLOAT NULL DEFAULT NULL) COLLATE='utf8mb4_general_ci';
