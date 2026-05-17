import { Link } from "react-router-dom";
import type { Listing } from "../api/client";
import { formatPrice } from "../api/client";

type Props = { listing: Listing };

export default function ListingCard({ listing }: Props) {
  return (
    <article className="card">
      <h3>
        <Link to={`/listing/${listing.id}`}>{listing.title}</Link>
      </h3>
      <p>{listing.description.slice(0, 80)}</p>
      <p className="price">{formatPrice(listing.price_cents)}</p>
    </article>
  );
}
