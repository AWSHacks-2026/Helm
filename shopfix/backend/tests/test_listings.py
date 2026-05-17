def test_create_list_and_search(client):
    client.post(
        "/auth/register",
        json={"email": "seller@test.com", "password": "secret123", "display_name": "Seller"},
    )
    login = client.post("/auth/login", json={"email": "seller@test.com", "password": "secret123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    created = client.post(
        "/listings",
        headers=headers,
        json={"title": "Handmade Mug", "description": "Ceramic", "price_cents": 2500, "tags": ["home"]},
    )
    assert created.status_code == 201
    listed = client.get("/listings?q=mug")
    assert listed.status_code == 200
    items = listed.json()
    assert len(items) >= 1
    assert items[0]["title"] == "Handmade Mug"
