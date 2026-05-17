import { useEffect, useState } from "react";
import ListingCard from "../components/ListingCard";
import { fetchListings, type Listing } from "../api/client";

export default function HomePage() {
  const [listings, setListings] = useState<Listing[]>([]);
  const [q, setQ] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    fetchListings()
      .then(setListings)
      .catch(() => setError("Could not load listings. Is the API running on :8001?"));
  }, []);

  async function search(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    try {
      setListings(await fetchListings(q || undefined));
    } catch {
      setError("Search failed");
    }
  }

  return (
    <div className="container">
      <h1>Discover handmade goods</h1>
      <form onSubmit={search}>
        <input placeholder="Search mugs, scarves…" value={q} onChange={(e) => setQ(e.target.value)} />
        <button type="submit">Search</button>
      </form>
      {error && <p>{error}</p>}
      <div className="grid">
        {listings.map((l) => (
          <ListingCard key={l.id} listing={l} />
        ))}
      </div>
    </div>
  );
}
