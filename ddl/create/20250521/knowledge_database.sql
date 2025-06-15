CREATE TABLE `knowledge_database` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL COMMENT '知识库名称',
  `description` text COMMENT '知识库描述',
  `embedding_model_id` int DEFAULT NULL COMMENT '嵌入模型ID',
  `vector_dimension` int NOT NULL DEFAULT '384' COMMENT '向量维度',
  `index_type` varchar(50) NOT NULL COMMENT '索引类型',
  `doc_count` int NOT NULL DEFAULT '0' COMMENT '文档数量',
  `user_id` int NOT NULL COMMENT '创建人ID',
  `username` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci NOT NULL,
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_user_name` (`user_id`,`name`),
  KEY `idx_creator` (`user_id`),
  KEY `idx_embedding_model_id` (`embedding_model_id`),
  CONSTRAINT `fk_knowledge_database_embedding_model` FOREIGN KEY (`embedding_model_id`) REFERENCES `embedding_model` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB AUTO_INCREMENT=18 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识库表';