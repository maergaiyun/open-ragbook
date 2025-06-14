CREATE TABLE `llmmodel` (
  `id` int NOT NULL AUTO_INCREMENT,
  `provider_id` int NOT NULL COMMENT '所属服务商ID',
  `name` varchar(100) NOT NULL COMMENT '模型名称',
  `model_type` varchar(100) NOT NULL COMMENT '模型类型',
  `api_key` varchar(200) NOT NULL COMMENT 'API Key',
  `base_url` varchar(200) DEFAULT NULL COMMENT 'Base URL',
  `max_tokens` int DEFAULT '4096' COMMENT '最大Token数',
  `temperature` float DEFAULT '0.7' COMMENT '温度参数',
  `is_default` tinyint(1) DEFAULT '0' COMMENT '是否默认',
  `user_id` int NOT NULL DEFAULT '1' COMMENT '所属用户ID',
  `username` varchar(100) DEFAULT NULL COMMENT '创建人姓名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_model_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='大模型配置';