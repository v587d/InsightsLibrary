from models import FileModel, ContentModel
from tinydb.operations import delete
file = FileModel()
content = ContentModel()
# file_id = "190090db-8817-4cb0-a0ce-631566744750"
# update_dict = {
#     "source": "PWC",
#     "uploader": "admin",
#     "language": "zh",
#     "topic": "Economy and Trade",
#     "published_data": "2025-04-02"
# }
# file.update_file(file_id, **update_dict)

def remove_published_data_field():
    """从所有文件记录中删除 published_data 字段"""
    file_model = FileModel()

    # 获取所有文件记录
    all_files = file_model.get_all_files()
    print(f"找到 {len(all_files)} 个文件记录")

    # 遍历所有文件记录
    for file_record in all_files:
        file_id = file_record.get('file_id')

        if not file_id:
            print(f"跳过无效记录: {file_id} - 缺少 file_id")
            continue

        # 检查是否存在 published_data 字段
        if 'published_data' in file_record:
            try:
                # 使用 TinyDB 的 delete 操作符删除字段
                file_model.files.update(
                    delete('published_data'),
                    file_model.query.file_id == file_id
                )
                print(f"成功删除 {file_id} 的 published_data 字段")
            except Exception as e:
                print(f"处理 {file_id} 时出错: {e}")
        else:
            print(f"{file_id} 无 published_data 字段，无需操作")

if __name__ == "__main__":
    pass
