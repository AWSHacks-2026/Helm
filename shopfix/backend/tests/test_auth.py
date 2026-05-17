def test_register_and_login(client):
    reg = client.post(
        "/auth/register",
        json={"email": "buyer@test.com", "password": "secret123", "display_name": "Buyer"},
    )
    assert reg.status_code == 201
    login = client.post("/auth/login", json={"email": "buyer@test.com", "password": "secret123"})
    assert login.status_code == 200
    body = login.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
