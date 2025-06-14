-- 修复大模型服务商表的唯一性约束
-- 将全局唯一改为用户级别唯一
-- 执行时间：2024-12-XX

-- 删除原有的全局唯一约束
ALTER TABLE `llmprovider` DROP INDEX `code`;

-- 添加用户级别的唯一约束
ALTER TABLE `llmprovider` ADD UNIQUE KEY `uk_user_code` (`user_id`, `code`);
ALTER TABLE `llmprovider` ADD UNIQUE KEY `uk_user_name` (`user_id`, `name`);

-- 添加索引优化查询性能
ALTER TABLE `llmprovider` ADD INDEX `idx_code` (`code`);
ALTER TABLE `llmprovider` ADD INDEX `idx_name` (`name`); 