CREATE TABLE `llmprovider` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '服务商名称',
  `code` varchar(50) NOT NULL COMMENT '服务商标识',
  `desc` text COMMENT '描述',
  `user_id` int NOT NULL DEFAULT '1' COMMENT '所属用户ID',
  `username` varchar(100) DEFAULT NULL COMMENT '创建人姓名',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_code` (`user_id`,`code`),
  UNIQUE KEY `uk_user_name` (`user_id`,`name`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_provider_user_id` (`user_id`),
  KEY `idx_code` (`code`),
  KEY `idx_name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='大模型服务商';