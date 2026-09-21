def test_health(client): assert client.get("/health").json() == {"status": "ok"}
def test_status_page(client): assert "Status: ok" in client.get("/").text
