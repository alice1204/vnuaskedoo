from fastapi.testclient import TestClient

from app import app

from services.student_service import (
    get_current_student_id,
)


client = TestClient(app)

def test_root():

    response = client.get("/")

    assert response.status_code == 200


def test_schedule_endpoint():

    app.dependency_overrides[
        get_current_student_id
    ] = lambda: "671234"

    try:
        response = client.post(
            "/schedule",
            json={
                "target_credits": 18,
                "allow_early": True,
            },
        )

        assert response.status_code == 200

        data = response.json()

        assert data["success"] is True
        assert data["total_credits"] == 18
    finally:
        app.dependency_overrides.clear()

def test_me_endpoint():

    app.dependency_overrides[
        get_current_student_id
    ] = lambda: "671234"

    try:
        response = client.get(
            "/me"
        )

        assert response.status_code == 200

        data = response.json()

        assert (
            data["student_id"]
            == "671234"
        )

        assert (
            data["current_semester"]
            == 4
        )
    finally:
        app.dependency_overrides.clear()

def test_unknown_logged_in_student_returns_404():

    app.dependency_overrides[
        get_current_student_id
    ] = lambda: "999999"

    try:
        response = client.post(
            "/schedule",
            json={
                "target_credits": 18,
                "allow_early": True,
            },
        )

        assert (
            response.status_code
            == 404
        )

    finally:
        app.dependency_overrides.clear()


def test_credit_below_minimum_returns_422():

    response = client.post(
        "/schedule",
        json={
            "target_credits": 10,
            "allow_early": True,
        },
    )

    assert response.status_code == 422


def test_credit_above_maximum_returns_422():

    response = client.post(
        "/schedule",
        json={
            "target_credits": 30,
            "allow_early": True,
        },
    )

    assert response.status_code == 422

def test_schedule_rejects_student_id():

    response = client.post(
        "/schedule",
        json={
            "student_id": "999999",
            "target_credits": 18,
            "allow_early": True,
        },
    )

    assert response.status_code == 422