from app.db.tables import Image
from sqladmin import ModelView


class ImageView(ModelView, model=Image):
    column_list = "__all__"
    column_searchable_list = [Image.status, Image.user_id, Image.id]
    column_sortable_list = [Image.created_at, Image.updated_at]
    column_default_sort = [(Image.created_at, True)]

