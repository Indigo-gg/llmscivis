import pymongo

# 连接到本地 MongoDB 实例
client = pymongo.MongoClient('mongodb://localhost:27017/')

# 创建或选择数据库
db = client['code_database']

# 创建或选择集合（表）
collection = db['code_snippets']

# 插入文档
def insert_code_snippet(code, metadata):
    document = {
        'code': code,
        'metadata': metadata
    }
    return collection.insert_one(document)

# 查询文档
def find_code_snippet(query):
    return collection.find_one(query)

# 更新文档
def update_code_snippet(filter_query, update_data):
    return collection.update_one(filter_query, {'$set': update_data})

# 删除文档
def delete_code_snippet(filter_query):
    return collection.delete_one(filter_query)