-- example 데이터베이스 및 todos 테이블 생성 스크립트
-- MySQL Workbench 또는 mysql CLI에서 실행

CREATE DATABASE IF NOT EXISTS example
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

USE example;

CREATE TABLE IF NOT EXISTS todos (
    id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    task TEXT NOT NULL
);
