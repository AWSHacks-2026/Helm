import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { addToCart, fetchListing, formatPrice, type Listing } from "../api/client";

export default function ListingPage() {
  const { id } = useParams();
  const [listing, setListing] = useState<Listing | null>(null);
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (id) fetchListing(Number(id)).then(setListing).catch(() => setMsg("Not found"));
  }, [id]);

  async function onAdd() {
    if (!listing) return;
    try {
      await addToCart(listing.id);
      setMsg("Added to cart");
    } catch {
      setMsg("Log in to add to cart");
    }
  }

  if (!listing) return <div className="container">{msg || "Loading…"}</div>;

  return (
    <div className="container card">
      <h1>{listing.title}</h1>
      <p>{listing.description}</p>
      <p className="price">{formatPrice(listing.price_cents)}</p>
      <button type="button" onClick={onAdd}>
        Add to cart
      </button>
      {msg && <p>{msg}</p>}
    </div>
  );
}
