import os
import shutil
import uuid

from fastapi import HTTPException
from sqlalchemy import delete
from starlette import status

from app.constants import TEMP_FILE_FOLDER
from app.db.errors import DoesNotExist
from app.db.tables.enums import ImageUrlType
from app.db.tables.posts import Post
from app.services.s3 import S3Service

from app.db.repositories.posts import PostsRepository

s3 = S3Service()


class PostsManager:
    @staticmethod
    async def delete_post(db, post_id: int, user_id: int):
        posts_repo = PostsRepository(db)
        try:
            post_db_obj = await posts_repo.get_by_id(post_id)
        except DoesNotExist:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Post does not exist",
            )
        if post_db_obj.user_id != user_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only post creator can delete the post",
            )

        if post_db_obj.image_url_type.name == ImageUrlType.absolute.name:
            image_url = post_db_obj.image_url
            _, photo_key = image_url.rsplit("/", 1)
            s3.delete_photo(photo_key)

        res = await db.execute(delete(Post).where(Post.id == post_id))
        return "ok"

    @staticmethod
    async def upload_image(image):
        filename = image.filename
        _, extension = filename.rsplit(".", 1)
        name = f"{uuid.uuid4()}.{extension}"
        path = os.path.join(TEMP_FILE_FOLDER, name)
        with open(path, "w+b") as buffer:
            shutil.copyfileobj(image.file, buffer)
        photo_url = s3.upload_photo(path, name, extension)
        os.remove(path)
        return {"filename": photo_url}
