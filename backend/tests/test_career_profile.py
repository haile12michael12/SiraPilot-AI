from tests.helpers import register_verified_user


def test_profile_and_skill_crud_are_scoped_to_authenticated_user(client, monkeypatch) -> None:
    first_token = register_verified_user(client, monkeypatch, "first@example.com")
    first_headers = {"Authorization": f"Bearer {first_token}"}
    profile = client.patch(
        "/api/v1/career-profile",
        json={
            "first_name": "First",
            "headline": "Product designer",
            "onboarding_step": 2,
        },
        headers=first_headers,
    )
    assert profile.status_code == 200
    assert profile.json()["first_name"] == "First"
    assert profile.json()["onboarding_step"] == 2

    created = client.post(
        "/api/v1/career-profile/entries/skills",
        json={"name": "Accessible design", "proficiency_level": "advanced"},
        headers=first_headers,
    )
    assert created.status_code == 201
    skill_id = created.json()["id"]
    assert created.json()["proficiency_level"] == "advanced"

    second_token = register_verified_user(client, monkeypatch, "second@example.com")
    second_headers = {"Authorization": f"Bearer {second_token}"}
    assert client.get(
        f"/api/v1/career-profile/entries/skills",
        headers=second_headers,
    ).json() == []
    assert client.patch(
        f"/api/v1/career-profile/entries/skills/{skill_id}",
        json={"name": "Taken over"},
        headers=second_headers,
    ).status_code == 404
    assert client.delete(
        f"/api/v1/career-profile/entries/skills/{skill_id}",
        headers=second_headers,
    ).status_code == 404


def test_preferences_and_onboarding_progress_persist(client, monkeypatch) -> None:
    token = register_verified_user(client, monkeypatch, "goals@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    saved = client.patch(
        "/api/v1/career-profile/preferences",
        json={
            "career_goal": "Move into engineering leadership",
            "remote_preference": "remote",
            "minimum_salary": 120000,
        },
        headers=headers,
    )
    assert saved.status_code == 200
    options = client.put(
        "/api/v1/career-profile/preference-options",
        json={
            "items": [
                {"kind": "job_title", "value": "Engineering manager"},
                {"kind": "industry", "value": "Healthcare technology"},
                {"kind": "location", "value": "Remote"},
            ]
        },
        headers=headers,
    )
    assert options.status_code == 200
    assert len(options.json()) == 3

    completed = client.post("/api/v1/career-profile/onboarding/complete", headers=headers)
    assert completed.status_code == 200
    assert completed.json()["onboarding_step"] == 9
    assert completed.json()["onboarding_completed_at"] is not None