-- EvalVerse Database Schema
-- Generated from Alembic migrations
-- Database: evaluation_platform
-- Character Set: utf8mb4
-- Collation: utf8mb4_unicode_ci

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS `evaluation_platform` DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE `evaluation_platform`;

-- ============================================
-- Core Tables
-- ============================================

-- Datasets table
CREATE TABLE IF NOT EXISTS `datasets` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `status` VARCHAR(20) DEFAULT 'Available',
  `item_count` BIGINT DEFAULT 0,
  `change_uncommitted` BOOLEAN DEFAULT FALSE,
  `latest_version` VARCHAR(50),
  `next_version_num` BIGINT DEFAULT 1,
  `biz_category` VARCHAR(100),
  `spec` JSON,
  `features` JSON,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_datasets_name` (`name`),
  KEY `ix_datasets_id` (`id`),
  KEY `ix_datasets_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dataset schemas table
CREATE TABLE IF NOT EXISTS `dataset_schemas` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `dataset_id` INT NOT NULL,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `field_definitions` JSON NOT NULL,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  PRIMARY KEY (`id`),
  KEY `ix_dataset_schemas_id` (`id`),
  CONSTRAINT `dataset_schemas_ibfk_1` FOREIGN KEY (`dataset_id`) REFERENCES `datasets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dataset versions table
CREATE TABLE IF NOT EXISTS `dataset_versions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `dataset_id` INT NOT NULL,
  `version` VARCHAR(50) NOT NULL,
  `description` TEXT,
  `schema_id` INT NOT NULL,
  `status` VARCHAR(20),
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  KEY `ix_dataset_versions_id` (`id`),
  CONSTRAINT `dataset_versions_ibfk_1` FOREIGN KEY (`dataset_id`) REFERENCES `datasets` (`id`),
  CONSTRAINT `dataset_versions_ibfk_2` FOREIGN KEY (`schema_id`) REFERENCES `dataset_schemas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dataset items table
CREATE TABLE IF NOT EXISTS `dataset_items` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `dataset_id` INT NOT NULL,
  `version_id` INT NOT NULL,
  `schema_id` INT,
  `item_key` VARCHAR(255),
  `data_content` JSON NOT NULL,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_dataset_items_item_key` (`item_key`),
  KEY `ix_dataset_items_id` (`id`),
  CONSTRAINT `dataset_items_ibfk_1` FOREIGN KEY (`dataset_id`) REFERENCES `datasets` (`id`),
  CONSTRAINT `dataset_items_ibfk_2` FOREIGN KEY (`version_id`) REFERENCES `dataset_versions` (`id`),
  CONSTRAINT `dataset_items_ibfk_3` FOREIGN KEY (`schema_id`) REFERENCES `dataset_schemas` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Dataset IO jobs table
CREATE TABLE IF NOT EXISTS `dataset_io_jobs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `dataset_id` INT NOT NULL,
  `job_type` VARCHAR(50) NOT NULL,
  `status` VARCHAR(20) DEFAULT 'Pending',
  `source_file` JSON,
  `target_dataset_id` INT,
  `field_mappings` JSON,
  `option` JSON,
  `total` BIGINT,
  `processed` BIGINT DEFAULT 0,
  `added` BIGINT DEFAULT 0,
  `progress` JSON,
  `sub_progresses` JSON,
  `errors` JSON,
  `started_at` DATETIME,
  `ended_at` DATETIME,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  KEY `ix_dataset_io_jobs_id` (`id`),
  KEY `ix_dataset_io_jobs_dataset_id` (`dataset_id`),
  KEY `ix_dataset_io_jobs_status` (`status`),
  CONSTRAINT `dataset_io_jobs_ibfk_1` FOREIGN KEY (`dataset_id`) REFERENCES `datasets` (`id`),
  CONSTRAINT `dataset_io_jobs_ibfk_2` FOREIGN KEY (`target_dataset_id`) REFERENCES `datasets` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Evaluators table
CREATE TABLE IF NOT EXISTS `evaluators` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `evaluator_type` ENUM('PROMPT', 'CODE', 'CUSTOM_RPC') NOT NULL,
  `latest_version` VARCHAR(50),
  `builtin` BOOLEAN DEFAULT FALSE,
  `box_type` ENUM('WHITE', 'BLACK'),
  `evaluator_info` JSON,
  `tags` JSON,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  KEY `ix_evaluators_id` (`id`),
  KEY `ix_evaluators_name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Evaluator versions table
CREATE TABLE IF NOT EXISTS `evaluator_versions` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `evaluator_id` INT NOT NULL,
  `version` VARCHAR(50) NOT NULL,
  `description` TEXT,
  `status` ENUM('DRAFT', 'SUBMITTED', 'ARCHIVED') NOT NULL DEFAULT 'DRAFT',
  `content` JSON NOT NULL,
  `input_schemas` JSON,
  `output_schemas` JSON,
  `prompt_content` JSON,
  `code_content` JSON,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  KEY `ix_evaluator_versions_id` (`id`),
  CONSTRAINT `evaluator_versions_ibfk_1` FOREIGN KEY (`evaluator_id`) REFERENCES `evaluators` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Evaluator records table
CREATE TABLE IF NOT EXISTS `evaluator_records` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `evaluator_version_id` INT NOT NULL,
  `experiment_id` INT,
  `experiment_run_id` INT,
  `dataset_item_id` INT,
  `turn_id` INT,
  `input_data` JSON NOT NULL,
  `output_data` JSON NOT NULL,
  `status` ENUM('UNKNOWN', 'SUCCESS', 'FAIL') NOT NULL DEFAULT 'UNKNOWN',
  `trace_id` VARCHAR(255),
  `log_id` VARCHAR(255),
  `ext` JSON,
  `created_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  KEY `ix_evaluator_records_id` (`id`),
  KEY `ix_evaluator_records_evaluator_version_id` (`evaluator_version_id`),
  KEY `ix_evaluator_records_experiment_id` (`experiment_id`),
  KEY `ix_evaluator_records_experiment_run_id` (`experiment_run_id`),
  KEY `ix_evaluator_records_dataset_item_id` (`dataset_item_id`),
  KEY `ix_evaluator_records_turn_id` (`turn_id`),
  KEY `ix_evaluator_records_trace_id` (`trace_id`),
  KEY `ix_evaluator_records_created_at` (`created_at`),
  CONSTRAINT `evaluator_records_ibfk_1` FOREIGN KEY (`evaluator_version_id`) REFERENCES `evaluator_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Experiments table
CREATE TABLE IF NOT EXISTS `experiments` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `dataset_version_id` INT NOT NULL,
  `evaluation_target_config` JSON,
  `evaluator_version_ids` JSON NOT NULL,
  `status` ENUM('pending', 'running', 'completed', 'failed', 'stopped', 'terminated', 'terminating') NOT NULL DEFAULT 'pending',
  `progress` INT DEFAULT 0,
  `item_concur_num` INT NOT NULL DEFAULT 1,
  `expt_type` ENUM('OFFLINE', 'ONLINE') NOT NULL DEFAULT 'OFFLINE',
  `max_alive_time` INT,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  KEY `ix_experiments_id` (`id`),
  KEY `ix_experiments_name` (`name`),
  CONSTRAINT `experiments_ibfk_1` FOREIGN KEY (`dataset_version_id`) REFERENCES `dataset_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Experiment runs table
CREATE TABLE IF NOT EXISTS `experiment_runs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `experiment_id` INT NOT NULL,
  `run_number` INT NOT NULL,
  `status` ENUM('pending', 'running', 'completed', 'failed', 'stopped', 'terminated', 'terminating') DEFAULT 'pending',
  `progress` INT DEFAULT 0,
  `started_at` DATETIME,
  `completed_at` DATETIME,
  `error_message` TEXT,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  PRIMARY KEY (`id`),
  KEY `ix_experiment_runs_id` (`id`),
  CONSTRAINT `experiment_runs_ibfk_1` FOREIGN KEY (`experiment_id`) REFERENCES `experiments` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Experiment results table
CREATE TABLE IF NOT EXISTS `experiment_results` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `experiment_id` INT NOT NULL,
  `run_id` INT NOT NULL,
  `dataset_item_id` INT NOT NULL,
  `evaluator_version_id` INT NOT NULL,
  `score` FLOAT,
  `reason` TEXT,
  `details` JSON,
  `actual_output` TEXT,
  `execution_time_ms` INT,
  `error_message` TEXT,
  `trace_id` VARCHAR(64),
  `created_at` DATETIME,
  PRIMARY KEY (`id`),
  KEY `ix_experiment_results_id` (`id`),
  KEY `idx_experiment_result_trace_id` (`trace_id`),
  CONSTRAINT `experiment_results_ibfk_1` FOREIGN KEY (`experiment_id`) REFERENCES `experiments` (`id`),
  CONSTRAINT `experiment_results_ibfk_2` FOREIGN KEY (`run_id`) REFERENCES `experiment_runs` (`id`),
  CONSTRAINT `experiment_results_ibfk_3` FOREIGN KEY (`dataset_item_id`) REFERENCES `dataset_items` (`id`),
  CONSTRAINT `experiment_results_ibfk_4` FOREIGN KEY (`evaluator_version_id`) REFERENCES `evaluator_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Experiment aggregate results table
CREATE TABLE IF NOT EXISTS `experiment_aggregate_results` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `experiment_id` INT NOT NULL,
  `evaluator_version_id` INT NOT NULL,
  `aggregate_data` JSON NOT NULL,
  `average_score` FLOAT,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  PRIMARY KEY (`id`),
  KEY `ix_experiment_aggregate_results_id` (`id`),
  KEY `ix_experiment_aggregate_results_experiment_id` (`experiment_id`),
  KEY `ix_experiment_aggregate_results_evaluator_version_id` (`evaluator_version_id`),
  CONSTRAINT `experiment_aggregate_results_ibfk_1` FOREIGN KEY (`experiment_id`) REFERENCES `experiments` (`id`),
  CONSTRAINT `experiment_aggregate_results_ibfk_2` FOREIGN KEY (`evaluator_version_id`) REFERENCES `evaluator_versions` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Experiment result exports table
CREATE TABLE IF NOT EXISTS `experiment_result_exports` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `experiment_id` INT NOT NULL,
  `status` ENUM('PENDING', 'RUNNING', 'SUCCESS', 'FAILED') NOT NULL DEFAULT 'PENDING',
  `file_url` VARCHAR(500),
  `file_name` VARCHAR(255),
  `error_message` TEXT,
  `started_at` DATETIME,
  `completed_at` DATETIME,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  KEY `ix_experiment_result_exports_id` (`id`),
  KEY `ix_experiment_result_exports_experiment_id` (`experiment_id`),
  CONSTRAINT `experiment_result_exports_ibfk_1` FOREIGN KEY (`experiment_id`) REFERENCES `experiments` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Model configs table
CREATE TABLE IF NOT EXISTS `model_configs` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `config_name` VARCHAR(255) NOT NULL,
  `model_type` VARCHAR(50) NOT NULL,
  `model_version` VARCHAR(100) NOT NULL,
  `api_key` TEXT NOT NULL,
  `api_base` VARCHAR(500),
  `temperature` FLOAT,
  `max_tokens` INT,
  `timeout` INT,
  `is_enabled` BOOLEAN NOT NULL DEFAULT FALSE,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_model_configs_config_name` (`config_name`),
  KEY `ix_model_configs_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Model sets table
CREATE TABLE IF NOT EXISTS `model_sets` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `name` VARCHAR(255) NOT NULL,
  `description` TEXT,
  `type` VARCHAR(50) NOT NULL,
  `config` JSON NOT NULL,
  `created_at` DATETIME,
  `updated_at` DATETIME,
  `created_by` VARCHAR(100),
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_model_sets_name` (`name`),
  KEY `ix_model_sets_id` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Traces table (for observability)
CREATE TABLE IF NOT EXISTS `traces` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trace_id` VARCHAR(64) NOT NULL,
  `service_name` VARCHAR(255),
  `operation_name` VARCHAR(255),
  `start_time` DATETIME NOT NULL,
  `end_time` DATETIME,
  `duration_ms` FLOAT,
  `status_code` VARCHAR(20),
  `attributes` JSON,
  `created_at` DATETIME,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_traces_trace_id` (`trace_id`),
  KEY `ix_traces_id` (`id`),
  KEY `ix_traces_service_name` (`service_name`),
  KEY `ix_traces_start_time` (`start_time`),
  KEY `idx_trace_service_time` (`service_name`, `start_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Spans table (for observability)
CREATE TABLE IF NOT EXISTS `spans` (
  `id` INT NOT NULL AUTO_INCREMENT,
  `trace_id` VARCHAR(64) NOT NULL,
  `span_id` VARCHAR(64) NOT NULL,
  `parent_span_id` VARCHAR(64),
  `name` VARCHAR(255) NOT NULL,
  `kind` VARCHAR(50),
  `start_time` DATETIME NOT NULL,
  `end_time` DATETIME,
  `duration_ms` FLOAT,
  `status_code` VARCHAR(20),
  `status_message` TEXT,
  `attributes` JSON,
  `events` JSON,
  `links` JSON,
  `created_at` DATETIME,
  PRIMARY KEY (`id`),
  UNIQUE KEY `ix_spans_span_id` (`span_id`),
  KEY `ix_spans_id` (`id`),
  KEY `ix_spans_trace_id` (`trace_id`),
  KEY `ix_spans_parent_span_id` (`parent_span_id`),
  KEY `idx_span_trace_id` (`trace_id`),
  KEY `idx_span_parent` (`parent_span_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

SET FOREIGN_KEY_CHECKS = 1;

