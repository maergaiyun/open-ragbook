CREATE TABLE `chat_message` (
  `id` int NOT NULL AUTO_INCREMENT,
  `conversation_id` int NOT NULL COMMENT '对话ID',
  `user_id` int NOT NULL DEFAULT '1' COMMENT '所属用户ID',
  `role` varchar(20) NOT NULL COMMENT '角色(user/assistant)',
  `content` text NOT NULL COMMENT '消息内容',
  `citations` json DEFAULT NULL COMMENT '引用来源',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_conversation_id` (`conversation_id`),
  KEY `idx_message_user_id` (`user_id`),
  CONSTRAINT `chat_message_ibfk_1` FOREIGN KEY (`conversation_id`) REFERENCES `chat_conversation` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=67 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='聊天消息表';