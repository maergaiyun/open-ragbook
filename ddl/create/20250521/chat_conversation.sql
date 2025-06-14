CREATE TABLE `chat_conversation` (
  `id` int NOT NULL AUTO_INCREMENT,
  `title` varchar(200) NOT NULL COMMENT '对话标题',
  `knowledge_base_id` int NOT NULL COMMENT '知识库ID',
  `knowledge_base_name` varchar(100) NOT NULL COMMENT '知识库名称',
  `model_id` int NOT NULL COMMENT '模型ID',
  `model_name` varchar(100) NOT NULL COMMENT '模型名称',
  `user_id` int DEFAULT NULL COMMENT '用户ID',
  `username` varchar(50) DEFAULT NULL COMMENT '用户名',
  `message_count` int DEFAULT '0' COMMENT '消息数量',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_kb_id` (`knowledge_base_id`),
  KEY `idx_model_id` (`model_id`),
  KEY `idx_conversation_user_id` (`user_id`)
) ENGINE=InnoDB AUTO_INCREMENT=28 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='聊天对话表';