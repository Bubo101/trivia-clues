from fastapi import APIRouter, Response, status
from pydantic import BaseModel
import psycopg

# Using routers for organization
# See https://fastapi.tiangolo.com/tutorial/bigger-applications/
router = APIRouter()


class CategoryIn(BaseModel):
    title: str


class CategoryOut(BaseModel):
    id: int
    title: str
    canon: bool

class CategoryWithClueCount(CategoryOut):
    num_clues: int

class Categories(BaseModel):
    page_count: int
    categories: list[CategoryWithClueCount]


class Message(BaseModel):
    message: str


@router.get("/api/categories", response_model=Categories)
def categories_list(page: int = 0):
    # Uses the environment variables to connect
    # In development, see the docker-compose.yml file for
    #   the PG settings in the "environment" section
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT c.id, c.title, c.canon, COUNT(cl.*) as num_clues
                FROM categories c
                LEFT OUTER JOIN clues cl 
                ON (c.id = cl.category_id)
                GROUP BY c.id,c.title,c.canon
                ORDER BY c.title
                LIMIT 100 OFFSET %s
            """,
                [page * 100],
            )

            results = []
            for row in cur.fetchall():
                record = {}
                for i, column in enumerate(cur.description):
                    record[column.name] = row[i]
                results.append(record)

            cur.execute(
                """
                SELECT COUNT(*) FROM categories;
            """
            )
            raw_count = cur.fetchone()[0]
            page_count = (raw_count // 100) + 1

            return Categories(page_count=page_count, categories=results)


@router.get(
    "/api/categories/{category_id}",
    response_model=CategoryOut,
    responses={404: {"model": Message}},
)
def get_category(category_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, title, canon
                FROM categories
                WHERE id = %s
            """,
                [category_id],
            )
            row = cur.fetchone()
            if row is None:
                response.status_code = status.HTTP_404_NOT_FOUND
                return {"message": "Category not found"}
            record = {}
            for i, column in enumerate(cur.description):
                record[column.name] = row[i]
            return record


@router.post(
    "/api/categories",
    response_model=CategoryOut,
    responses={409: {"model": Message}},
)
def create_category(category: CategoryIn, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            try:
                # Uses the RETURNING clause to get the data
                # just inserted into the database. See
                # https://www.postgresql.org/docs/current/sql-insert.html
                cur.execute(
                    """
                    INSERT INTO categories (title, canon)
                    VALUES (%s, false)
                    RETURNING id, title, canon;
                """,
                    [category.title],
                )
            except psycopg.errors.UniqueViolation:
                # status values at https://github.com/encode/starlette/blob/master/starlette/status.py
                response.status_code = status.HTTP_409_CONFLICT
                return {
                    "message": "Could not create duplicate category",
                }
            row = cur.fetchone()
            record = {}
            for i, column in enumerate(cur.description):
                record[column.name] = row[i]
            return record


@router.put(
    "/api/categories/{category_id}",
    response_model=CategoryOut,
    responses={404: {"model": Message}},
)
def update_category(category_id: int, category: CategoryIn, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE categories
                SET title = %s
                WHERE id = %s;
            """,
                [category.title, category_id],
            )
    return get_category(category_id, response)


@router.delete(
    "/api/categories/{category_id}",
    response_model=Message,
    responses={400: {"model": Message}},
)
def remove_category(category_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    """
                    DELETE FROM categories
                    WHERE id = %s;
                """,
                    [category_id],
                )
                return {
                    "message": "Success",
                }
            except psycopg.errors.ForeignKeyViolation:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return {
                    "message": "Cannot delete category because it has clues",
                }
