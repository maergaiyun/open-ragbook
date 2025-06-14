CREATE TABLE `knowledge_document_chunk` (
  `id` int NOT NULL AUTO_INCREMENT,
  `document_id` int NOT NULL COMMENT '所属文档ID',
  `database_id` int NOT NULL COMMENT '所属知识库ID',
  `chunk_index` int NOT NULL COMMENT '分块索引',
  `content` text NOT NULL COMMENT '分块内容',
  `vector_id` varchar(64) DEFAULT NULL COMMENT '向量ID',
  `create_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_document_id` (`document_id`),
  KEY `idx_database_id` (`database_id`),
  CONSTRAINT `fk_chunk_database` FOREIGN KEY (`database_id`) REFERENCES `knowledge_database` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chunk_document` FOREIGN KEY (`document_id`) REFERENCES `knowledge_document` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB AUTO_INCREMENT=45 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='知识文档分块表';