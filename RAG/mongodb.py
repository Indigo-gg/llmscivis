import pymongo
from pymongo.results import InsertOneResult, UpdateResult, DeleteResult
from typing import Dict, Any, Optional

# 连接到本地 MongoDB 实例
# 建议将连接字符串作为参数或环境变量，以提高灵活性和安全性
# client = pymongo.MongoClient('mongodb://localhost:27017/')

# 更好的实践：使用上下文管理器或在程序结束时显式关闭连接
# 对于脚本，可以保持当前方式，但对于长期运行的服务，需要考虑连接池和关闭
class MongoDBManager:
    def __init__(self, host: str = 'localhost', port: int = 27017, db_name: str = 'code_database', collection_name: str = 'code_snippets'):
        """
        初始化 MongoDB 连接和集合。
        """
        self.client = pymongo.MongoClient(f'mongodb://{host}:{port}/')
        self.db = self.client[db_name]
        self.collection = self.db[collection_name]
        print(f"成功连接到 MongoDB: {host}:{port}, 数据库: {db_name}, 集合: {collection_name}")

        # 确保为 FAISS ID 创建索引，提高查询效率
        # index_name = "faiss_id_index"
        # if index_name not in self.collection.index_information():
        #     self.collection.create_index("faiss_id", unique=True, name=index_name)
        #     print(f"已创建或验证索引: {index_name}")
        # 注意：这里的 unique=True 需要根据你的 faiss_id 生成逻辑来决定
        # 如果 faiss_id 总是唯一，unique=True 是好的。如果可能重复，则不要设置 unique=True


    def insert_code_snippet(self, code_document: Dict[str, Any]) -> InsertOneResult:
        """
        插入单个文档。
        Args:
            code_document (Dict[str, Any]): 要插入的文档数据。
        Returns:
            InsertOneResult: 插入操作的结果。包含 inserted_id。
        """
        try:
            result = self.collection.insert_one(code_document)
            print(f"文档插入成功，ID: {result.inserted_id}，代码片段: {code_document['code'][:10]}")
            return result
        except pymongo.errors.PyMongoError as e:
            print(f"插入文档时发生错误: {e}")
            raise # 重新抛出异常以便上层代码处理


    def find_code_snippet(self, query: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        查询单个文档。
        Args:
            query (Dict[str, Any]): 查询条件。
        Returns:
            Optional[Dict[str, Any]]: 匹配的文档，如果没有找到则返回 None。
        """
        try:
            document = self.collection.find_one(query)
            # if document:
            #     print(f"找到匹配文档: {query}")
            # else:
            #     print(f"未找到匹配文档: {query}")
            return document
        except pymongo.errors.PyMongoError as e:
            print(f"查询文档时发生错误: {e}")
            raise


    def update_code_snippet(self, filter_query: Dict[str, Any], update_data: Dict[str, Any]) -> UpdateResult:
        """
        更新单个文档。
        Args:
            filter_query (Dict[str, Any]): 用于查找要更新文档的条件。
            update_data (Dict[str, Any]): 要更新的字段及其新值。
        Returns:
            UpdateResult: 更新操作的结果。
        """
        try:
            result = self.collection.update_one(filter_query, {'$set': update_data})
            print(f"文档更新完成。匹配数量: {result.matched_count}, 修改数量: {result.modified_count}")
            return result
        except pymongo.errors.PyMongoError as e:
            print(f"更新文档时发生错误: {e}")
            raise


    def delete_code_snippet(self, filter_query: Dict[str, Any]) -> DeleteResult:
        """
        删除单个文档。
        Args:
            filter_query (Dict[str, Any]): 用于查找要删除文档的条件。
        Returns:
            DeleteResult: 删除操作的结果。
        """
        try:
            result = self.collection.delete_one(filter_query)
            print(f"文档删除完成。删除数量: {result.deleted_count}")
            return result
        except pymongo.errors.PyMongoError as e:
            print(f"删除文档时发生错误: {e}")
            raise

    def close_connection(self):
        """
        关闭 MongoDB 客户端连接。
        """
        if self.client:
            self.client.close()
            print("MongoDB 连接已关闭。")

    def clear_collection(self) -> DeleteResult:
        """
        清空当前集合中的所有文档。
        """
        try:
            result = self.collection.delete_many({})
            print(f"集合已清空。删除数量: {result.deleted_count}")
            return result
        except pymongo.errors.PyMongoError as e:
            print(f"清空集合时发生错误: {e}")
            raise

# 示例用法 (假设这部分代码放在 RAG.mongodb 中)
if __name__ == '__main__':
#   pass
    # 初始化 MongoDB 连接
    mongo_manager = MongoDBManager()

    # 清空集合
    result = mongo_manager.clear_collection()
    print(result)