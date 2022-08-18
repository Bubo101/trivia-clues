from fastapi import APIRouter, Response, status
from pydantic import BaseModel
from datetime import datetime
import psycopg

router = APIRouter()


class GameOut(BaseModel):
    id: int
    episode_id: int
    aired: str
    canon: bool
    total_amount_won: int


class Category(BaseModel):
    id: int
    title: str


class Clue(BaseModel):
    id: int
    answer: str
    question: str
    value: int
    invalid_count: int
    category: Category


class CustomGameOut(BaseModel):
    id: int
    created_on: datetime
    clues: list[Clue]


class Message(BaseModel):
    message: str


@router.get(
    "/api/games/{game_id}",
    response_model=GameOut,
    responses={404: {"model": Message}},
)
def get_game(game_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT g.id, g.episode_id, g.aired, g.canon, SUM(c.value) AS total_amount_won
                FROM games AS g
                LEFT JOIN clues AS c ON g.id = c.game_id
                WHERE g.id = %s
                GROUP BY g.id
            """,
                [game_id],
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
    "/api/custom-games",
    response_model=CustomGameOut,
    responses={404: {"model": Message}},
)
def create_custom_game(response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    cl.id AS clue_id, cl.answer, cl.question, cl.value,
                    cl.invalid_count, cat.id AS category_id, cat.title
                FROM clues AS cl
                LEFT JOIN categories AS cat ON cl.category_id = cat.id
                WHERE cl.canon = true
                ORDER BY RANDOM()
                LIMIT 30
            """
            )

            clue_fields = [
                "clue_id",
                "answer",
                "question",
                "value",
                "invalid_count",
            ]
            category_fields = [
                "category_id",
                "title",
            ]
            clue_list = []
            for row in cur.fetchall():
                clue = {}
                for i, column in enumerate(cur.description):
                    if column.name in clue_fields:
                        clue[column.name] = row[i]
                clue["id"] = clue["clue_id"]

                category = {}
                for i, column in enumerate(cur.description):
                    if column.name in category_fields:
                        category[column.name] = row[i]
                category["id"] = category["category_id"]

                clue["category"] = category
                
                clue_list.append(clue)

            with conn.transaction():
                cur.execute(
                    """
                    INSERT INTO game_definitions (created_on)
                    VALUES (CURRENT_TIMESTAMP)
                    RETURNING *
                """
                )
                custom_game = cur.fetchone()
                game_id = custom_game[0]
                game_timestamp = custom_game[1]

                for clue in clue_list:
                    cur.execute(
                        """
                        INSERT INTO game_definition_clues (game_definition_id, clue_id)
                        VALUES (%s, %s)
                    """,
                    [game_id, clue["id"]],
                    )

                record = {
                    "id": game_id,
                    "created_on": game_timestamp,
                    "clues": clue_list
                }
                return record


@router.get(
    "/api/custom-games/{custom_game_id}",
    response_model=CustomGameOut,
    responses={404: {"model": Message}},
)
def get_custom_game(custom_game_id: int, response: Response):
    with psycopg.connect() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    gd.created_on,
                    cl.id AS clue_id, cl.answer, cl.question, cl.value, cl.invalid_count,
                    cat.id AS category_id, cat.title
                FROM game_definitions AS gd
                LEFT JOIN game_definition_clues AS gdc ON gd.id = gdc.game_definition_id
                LEFT JOIN clues AS cl ON gdc.clue_id = cl.id
                LEFT JOIN categories AS cat ON cl.category_id = cat.id
                WHERE gd.id = %s
            """,
            [custom_game_id],
            )

            data = cur.fetchall()
            game_timestamp = data[0][0]
            clue_fields = [
                "clue_id",
                "answer",
                "question",
                "value",
                "invalid_count",
            ]
            category_fields = [
                "category_id",
                "title",
            ]
            clue_list = []
            for row in data:
                clue = {}
                for i, column in enumerate(cur.description):
                    if column.name in clue_fields:
                        clue[column.name] = row[i]
                clue["id"] = clue["clue_id"]

                category = {}
                for i, column in enumerate(cur.description):
                    if column.name in category_fields:
                        category[column.name] = row[i]
                category["id"] = category["category_id"]

                clue["category"] = category
                
                clue_list.append(clue)

            record = {
                "id": custom_game_id,
                "created_on": game_timestamp,
                "clues": clue_list
            }
            return record