from .categories import CategoryOut
from fastapi import APIRouter, Response, status
from pydantic import BaseModel
import psycopg
from .categories import CategoryOut
router = APIRouter()
class ClueOut(BaseModel):
    id: int
    answer: str
    question: str
    value: int
    invalid_count: int
    category: CategoryOut
    canon: bool

class Clues(BaseModel):
    page_count: int
    clues: list[ClueOut]
    
class Message(BaseModel):
    message: str
@router.get(
    "/api/clues/{clue_id}",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def get_clue(clue_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT clues.id as clue_id, clues.answer, clues.question, clues.value, clues.invalid_count, clues.canon as clue_canon,
                        categories.id as cat_id, categories.title, categories.canon as cat_canon
                FROM categories
                JOIN clues ON (clues.category_id = categories.id)
                WHERE clues.id = %s
                """,
                    [clue_id],
            )
            record = None
            row = cur.fetchone()
            if row:
                record = {}
                clue_fields = [
                    "clue_id",
                    "answer",
                    "question",
                    "value",
                    "invalid_count",
                    "clue_canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in clue_fields:
                        record[column.name] = row[i]
                record["id"] = record["clue_id"]
                record["canon"] = record["clue_canon"]
                category = {}
                category_fields = [
                    "cat_id",
                    "title",
                    "cat_canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in category_fields:
                        category[column.name] = row[i]
                category["id"] = category["cat_id"]
                category["canon"] = category["cat_canon"]
                record["category"] = category
            if record is None:
                response.status_code = status.HTTP_404_NOT_FOUND
            return record
@router.get(
    "/api/random-clue",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def get_random_clue(response: Response, valid: bool = True):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            if valid:
                # Choose random clue where invalid_count = 0
                cur.execute(
                    """
                    SELECT clues.id as clue_id, clues.answer, clues.question, clues.value, clues.invalid_count, clues.canon as clue_canon,
                        categories.id as cat_id, categories.title, categories.canon as cat_canon
                    FROM categories
                    JOIN clues ON (clues.category_id = categories.id)
                    WHERE clues.invalid_count = 0
                    ORDER BY RANDOM()
                    LIMIT 1
                    """
                )
            else:
                # Choose any random clue
                cur.execute(
                    """
                    SELECT clues.id as clue_id, clues.answer, clues.question, clues.value, clues.invalid_count, clues.canon as clue_canon,
                        categories.id as cat_id, categories.title, categories.canon as cat_canon
                    FROM categories
                    JOIN clues ON (clues.category_id = categories.id)
                    ORDER BY RANDOM()
                    LIMIT 1
                    """
                )
            record = None
            row = cur.fetchone()
            if row:
                record = {}
                clue_fields = [
                    "clue_id",
                    "answer",
                    "question",
                    "value",
                    "invalid_count",
                    "clue_canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in clue_fields:
                        record[column.name] = row[i]
                record["id"] = record["clue_id"]
                record["canon"] = record["clue_canon"]
                category = {}
                category_fields = [
                    "cat_id",
                    "title",
                    "cat_canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in category_fields:
                        category[column.name] = row[i]
                category["id"] = category["cat_id"]
                category["canon"] = category["cat_canon"]
                record["category"] = category
            if record is None:
                response.status_code = status.HTTP_404_NOT_FOUND
            return record  


@router.get("/api/clues", response_model=Clues)
def clues_list(page: int = 0, value: int = None):
    # Uses the environment variables to connect
    # In development, see the docker-compose.yml file for
    #   the PG settings in the "environment" section
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            if value:
                params = [value, page * 100]
                cur.execute(
                    """
                    SELECT clues.id as clue_id, clues.answer, clues.question, clues.value, clues.invalid_count, clues.category_id, clues.canon,
                        categories.id as cat_id, categories.title, categories.canon
                    FROM categories
                    JOIN clues ON (clues.category_id = categories.id)
                    WHERE value = %s
                    ORDER BY clues.id
                    LIMIT 100 OFFSET %s
                """,
                    params)
            else:
                cur.execute(
                    """
                    SELECT clues.id as clue_id, clues.answer, clues.question, clues.value, clues.invalid_count, clues.category_id, clues.canon,
                        categories.id as cat_id, categories.title, categories.canon
                    FROM categories
                    JOIN clues ON (clues.category_id = categories.id)
                    ORDER BY clues.id
                    LIMIT 100 OFFSET %s
                """,
                    [page * 100])
            results = []
            for row in cur.fetchall():
                record = {}
                clue_fields = [
                    "clue_id",
                    "answer",
                    "question",
                    "value",
                    "invalid_count",
                    "canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in clue_fields:
                        record[column.name] = row[i]
                record["id"] = record["clue_id"]
                category = {}
                category_fields = [
                    "cat_id",
                    "title",
                    "canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in category_fields:
                        category[column.name] = row[i]
                category["id"] = category["cat_id"]
                record["category"] = category
                
                results.append(record)
            cur.execute(
                """
                SELECT COUNT(*) FROM clues;
            """
            )
            raw_count = cur.fetchone()[0]
            page_count = (raw_count // 100) + 1
            return Clues(page_count=page_count, clues=results)


@router.delete(
    "/api/clues/{clue_id}",
    response_model=ClueOut,
    responses={404: {"model": Message}},
)
def delete_clue(clue_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                UPDATE clues
                SET invalid_count = invalid_count + 1
                WHERE id = %s
                """,
                    [clue_id],
            )
            cur.execute(
                """
                SELECT clues.id as clue_id, clues.answer, clues.question, clues.value, clues.invalid_count, clues.canon as clue_canon,
                        categories.id as cat_id, categories.title, categories.canon as cat_canon
                FROM categories
                JOIN clues ON (clues.category_id = categories.id)
                WHERE clues.id = %s
                """,
                    [clue_id],
            )
            record = None
            row = cur.fetchone()
            if row:
                record = {}
                clue_fields = [
                    "clue_id",
                    "answer",
                    "question",
                    "value",
                    "invalid_count",
                    "clue_canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in clue_fields:
                        record[column.name] = row[i]
                record["id"] = record["clue_id"]
                record["canon"] = record["clue_canon"]
                category = {}
                category_fields = [
                    "cat_id",
                    "title",
                    "cat_canon",
                ]
                for i, column in enumerate(cur.description):
                    if column.name in category_fields:
                        category[column.name] = row[i]
                category["id"] = category["cat_id"]
                category["canon"] = category["cat_canon"]
                record["category"] = category
            if record is None:
                response.status_code = status.HTTP_404_NOT_FOUND
            return record