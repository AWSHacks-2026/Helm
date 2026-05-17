const API = "/api";

export type Listing = {
  id: number;
  seller_id: number;
  title: string;
  description: string;
  price_cents: number;
  tags: string[];
};

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("shopfix_token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export async function fetchListings(q?: string): Promise<Listing[]> {
  const url = q ? `${API}/listings?q=${encodeURIComponent(q)}` : `${API}/listings`;
  const res = await fetch(url);
  if (!res.ok) throw new Error("Failed to load listings");
  return res.json();
}

export async function fetchListing(id: number): Promise<Listing> {
  const res = await fetch(`${API}/listings/${id}`);
  if (!res.ok) throw new Error("Not found");
  return res.json();
}

export async function login(email: string, password: string): Promise<void> {
  const res = await fetch(`${API}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Login failed");
  const data = await res.json();
  localStorage.setItem("shopfix_token", data.access_token);
}

export async function register(email: string, password: string, display_name: string): Promise<void> {
  const res = await fetch(`${API}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password, display_name }),
  });
  if (!res.ok) throw new Error("Register failed");
}

export async function addToCart(listingId: number, quantity = 1): Promise<void> {
  const res = await fetch(`${API}/cart/items`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify({ listing_id: listingId, quantity }),
  });
  if (!res.ok) throw new Error("Add to cart failed");
}

export async function fetchCart(): Promise<{ items: { listing: Listing; quantity: number }[]; total_cents: number }> {
  const res = await fetch(`${API}/cart`, { headers: authHeaders() });
  if (!res.ok) throw new Error("Cart failed");
  return res.json();
}

export async function checkout(): Promise<void> {
  const res = await fetch(`${API}/orders/checkout`, { method: "POST", headers: authHeaders() });
  if (!res.ok) throw new Error("Checkout failed");
}

export function formatPrice(cents: number): string {
  return `$${(cents / 100).toFixed(2)}`;
}
