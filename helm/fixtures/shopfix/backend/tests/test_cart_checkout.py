def test_add_to_cart_and_checkout(client):
    client.post("/auth/register", json={"email": "b@test.com", "password": "secret123", "display_name": "B"})
    token = client.post("/auth/login", json={"email": "b@test.com", "password": "secret123"}).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.post(
        "/listings",
        headers=headers,
        json={"title": "Scarf", "description": "Wool", "price_cents": 4000, "tags": []},
    ).json()
    add = client.post("/cart/items", headers=headers, json={"listing_id": listing["id"], "quantity": 1})
    assert add.status_code == 201
    order = client.post("/orders/checkout", headers=headers)
    assert order.status_code == 201
    body = order.json()
    assert body["total_cents"] == 4000
    assert len(body["items"]) == 1
