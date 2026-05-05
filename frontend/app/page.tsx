"use client";

import { FormEvent, useEffect, useMemo, useState } from "react";
import Image from "next/image";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

type User = {
  id: number;
  username: string;
  email: string;
  phone?: string | null;
  address?: string | null;
};

type Restaurant = {
  id: number;
  name: string;
  address: string;
  phone?: string | null;
  description?: string | null;
  image_url?: string | null;
  is_open: boolean;
};

type Plat = {
  id: number;
  nom: string;
  prix: number;
  description?: string | null;
  ingredients?: string | null;
  allergenes?: string | null;
  image_url?: string | null;
  is_available: boolean;
  restaurant_id: number;
};

type CartItem = {
  plat: Plat;
  quantite: number;
};

type OrderResponse = {
  id: number;
  restaurant_id: number;
  statut: string;
  statut_livraison: string;
  prix_total: number;
  items: Array<{ plat_id: number; quantite: number }>;
};

type AuthMode = "login" | "register";

function imageSrc(path?: string | null) {
  return path || "/images/bistro_du_code.jpg";
}

function formatPrice(value: number) {
  return `${value.toFixed(2)} €`;
}

async function parseApiResponse<T>(response: Response): Promise<T> {
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail =
      typeof data.detail === "string"
        ? data.detail
        : Array.isArray(data.detail)
          ? data.detail
              .map((error: { loc?: Array<string | number>; msg?: string }) => {
                const field = error.loc?.filter((part) => part !== "body").join(".");
                return field ? `${field}: ${error.msg}` : error.msg;
              })
              .join(" ")
          : "Erreur API";
    throw new Error(detail);
  }
  return data as T;
}

export default function Home() {
  const [authMode, setAuthMode] = useState<AuthMode>("login");
  const [token, setToken] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    return sessionStorage.getItem("token");
  });
  const [currentUser, setCurrentUser] = useState<User | null>(() => {
    if (typeof window === "undefined") return null;
    const savedUser = sessionStorage.getItem("user");
    return savedUser ? (JSON.parse(savedUser) as User) : null;
  });
  const [restaurants, setRestaurants] = useState<Restaurant[]>([]);
  const [plats, setPlats] = useState<Plat[]>([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");
  const [loadingAuth, setLoadingAuth] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [toast, setToast] = useState("");
  const [confirmedOrder, setConfirmedOrder] = useState<OrderResponse | null>(null);

  const authHeaders = useMemo<Record<string, string>>(() => {
    if (!token) return {} as Record<string, string>;
    return { Authorization: `Bearer ${token}` };
  }, [token]);

  const cartCount = cart.reduce((total, item) => total + item.quantite, 0);
  const cartTotal = cart.reduce((total, item) => total + item.plat.prix * item.quantite, 0);

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  }

  useEffect(() => {
    if (!currentUser || !token) return;

    const loadData = async () => {
      setLoadingData(true);
      try {
        const response = await fetch(`${API_URL}/restaurants/`);
        const data = await parseApiResponse<Restaurant[]>(response);
        setRestaurants(data);
      } catch (error) {
        notify(error instanceof Error ? error.message : "Impossible de charger les restaurants.");
      } finally {
        setLoadingData(false);
      }
    };

    loadData();
  }, [currentUser, token]);

  async function handleRegister(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    setAuthSuccess("");
    setLoadingAuth(true);

    const form = new FormData(event.currentTarget);
    const payload = {
      username: String(form.get("username") || "").trim(),
      email: String(form.get("email") || "").trim(),
      password: String(form.get("password") || ""),
      phone: String(form.get("phone") || "").trim() || null,
      address: String(form.get("address") || "").trim() || null,
    };

    try {
      const response = await fetch(`${API_URL}/users/`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      await parseApiResponse<User>(response);
      setAuthSuccess("Compte cree. Vous pouvez vous connecter.");
      setAuthMode("login");
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Inscription impossible.");
    } finally {
      setLoadingAuth(false);
    }
  }

  async function handleLogin(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setAuthError("");
    setAuthSuccess("");
    setLoadingAuth(true);

    const form = new FormData(event.currentTarget);
    const email = String(form.get("email") || "").trim();
    const password = String(form.get("password") || "");
    const loginBody = new FormData();
    loginBody.append("username", email);
    loginBody.append("password", password);

    try {
      const loginResponse = await fetch(`${API_URL}/auth/login`, {
        method: "POST",
        body: loginBody,
      });
      const loginData = await parseApiResponse<{ access_token: string }>(loginResponse);
      const userResponse = await fetch(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${loginData.access_token}` },
      });
      const user = await parseApiResponse<User>(userResponse);

      sessionStorage.setItem("token", loginData.access_token);
      sessionStorage.setItem("user", JSON.stringify(user));
      setToken(loginData.access_token);
      setCurrentUser(user);
      notify(`Bienvenue, ${user.username}`);
    } catch (error) {
      setAuthError(error instanceof Error ? error.message : "Connexion impossible.");
    } finally {
      setLoadingAuth(false);
    }
  }

  async function openRestaurant(restaurant: Restaurant) {
    setSelectedRestaurant(restaurant);
    setLoadingData(true);
    try {
      const response = await fetch(`${API_URL}/plats/restaurant/${restaurant.id}`);
      const data = await parseApiResponse<Plat[]>(response);
      setPlats(data);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (error) {
      notify(error instanceof Error ? error.message : "Impossible de charger le menu.");
    } finally {
      setLoadingData(false);
    }
  }

  function closeMenu() {
    setSelectedRestaurant(null);
    setPlats([]);
    setCartOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function quantityFor(platId: number) {
    return cart.find((item) => item.plat.id === platId)?.quantite || 0;
  }

  function addToCart(plat: Plat) {
    if (!selectedRestaurant) return;
    if (!plat.is_available) {
      notify("Ce plat n'est pas disponible.");
      return;
    }

    setCart((current) => {
      if (current.length > 0 && current[0].plat.restaurant_id !== selectedRestaurant.id) {
        notify("Panier vide: vous commandez maintenant dans un autre restaurant.");
        return [{ plat, quantite: 1 }];
      }

      const existing = current.find((item) => item.plat.id === plat.id);
      if (existing) {
        return current.map((item) =>
          item.plat.id === plat.id ? { ...item, quantite: item.quantite + 1 } : item,
        );
      }

      return [...current, { plat, quantite: 1 }];
    });
  }

  function changeQuantity(platId: number, delta: number) {
    setCart((current) =>
      current
        .map((item) =>
          item.plat.id === platId ? { ...item, quantite: item.quantite + delta } : item,
        )
        .filter((item) => item.quantite > 0),
    );
  }

  async function submitOrder() {
    if (!currentUser || !selectedRestaurant || cart.length === 0 || !token) return;

    try {
      const response = await fetch(`${API_URL}/commandes/`, {
        method: "POST",
        headers: {
          ...authHeaders,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          user_id: currentUser.id,
          restaurant_id: selectedRestaurant.id,
          items: cart.map((item) => ({
            plat_id: item.plat.id,
            quantite: item.quantite,
          })),
        }),
      });
      const order = await parseApiResponse<OrderResponse>(response);
      setConfirmedOrder(order);
      setCart([]);
      setCartOpen(false);
    } catch (error) {
      notify(error instanceof Error ? error.message : "Impossible de passer la commande.");
    }
  }

  function logout() {
    sessionStorage.removeItem("token");
    sessionStorage.removeItem("user");
    setToken(null);
    setCurrentUser(null);
    setSelectedRestaurant(null);
    setCart([]);
    setPlats([]);
    setCartOpen(false);
  }

  if (!currentUser) {
    return (
      <main className="auth-overlay">
        <section className="auth-split">
          <div className="auth-brand">
            <div className="brand-logo">MiamDelivery</div>
            <div className="brand-tagline">
              <h1>Commandez, regalez-vous.</h1>
              <p>Les meilleurs restaurants de votre ville, livres chez vous en quelques minutes.</p>
            </div>
            <div className="brand-circles" />
          </div>

          <div className="auth-form-panel">
            <div className="auth-tabs">
              <button
                className={`auth-tab ${authMode === "login" ? "active" : ""}`}
                onClick={() => setAuthMode("login")}
                type="button"
              >
                Connexion
              </button>
              <button
                className={`auth-tab ${authMode === "register" ? "active" : ""}`}
                onClick={() => setAuthMode("register")}
                type="button"
              >
                Inscription
              </button>
            </div>

            {authMode === "login" ? (
              <form className="auth-form active" onSubmit={handleLogin}>
                <div>
                  <div className="form-title">Bon retour</div>
                  <div className="form-subtitle">Connectez-vous pour acceder a votre compte</div>
                </div>
                {authError && <div className="auth-error">{authError}</div>}
                {authSuccess && <div className="auth-success">{authSuccess}</div>}
                <label className="form-group">
                  Adresse email
                  <input name="email" type="email" placeholder="vous@exemple.com" required />
                </label>
                <label className="form-group">
                  Mot de passe
                  <input name="password" type="password" placeholder="password123" required />
                </label>
                <button className="btn-submit" disabled={loadingAuth} type="submit">
                  {loadingAuth ? "Connexion..." : "Se connecter"}
                </button>
                <p className="demo-hint">Demo: arthur@example.com / password123</p>
              </form>
            ) : (
              <form className="auth-form active" onSubmit={handleRegister}>
                <div>
                  <div className="form-title">Creer un compte</div>
                  <div className="form-subtitle">Rejoignez MiamDelivery des maintenant</div>
                </div>
                {authError && <div className="auth-error">{authError}</div>}
                <div className="form-row">
                  <label className="form-group">
                    Nom d&apos;utilisateur
                    <input name="username" placeholder="johnDoe" required />
                  </label>
                  <label className="form-group">
                    Telephone
                    <input name="phone" placeholder="06 00 00 00 00" />
                  </label>
                </div>
                <label className="form-group">
                  Email
                  <input name="email" type="email" placeholder="vous@exemple.com" required />
                </label>
                <label className="form-group">
                  Adresse de livraison
                  <input name="address" placeholder="12 rue de la Paix, Paris" />
                </label>
                <label className="form-group">
                  Mot de passe
                  <input name="password" type="password" placeholder="password123" minLength={6} required />
                </label>
                <button className="btn-submit green" disabled={loadingAuth} type="submit">
                  {loadingAuth ? "Creation..." : "Creer mon compte"}
                </button>
              </form>
            )}
          </div>
        </section>
      </main>
    );
  }

  return (
    <main>
      <header className="app-header">
        <button className="logo-container" onClick={closeMenu} type="button">
          <span className="menu-mark">☰</span>
          <span className="logo">MiamDelivery</span>
        </button>
        <div className="header-right">
          <div className="user-badge">
            <span className="user-avatar">{currentUser.username.slice(0, 2).toUpperCase()}</span>
            <span>{currentUser.username}</span>
          </div>
          <button className="cart-btn" onClick={() => setCartOpen(true)} type="button">
            Panier
            {cartCount > 0 && <span className="cart-count visible">{cartCount}</span>}
          </button>
          <button className="logout-btn" onClick={logout} type="button">
            Deconnexion
          </button>
        </div>
      </header>

      <section className="container">
        {!selectedRestaurant ? (
          <>
            <div className="section-title">A la une</div>
            <div className="section-subtitle">Les meilleurs restos pres de chez vous</div>
            {loadingData ? (
              <p className="muted">Chargement...</p>
            ) : (
              <div className="grid">
                {restaurants.map((restaurant) => (
                  <button
                    className="resto-card"
                    key={restaurant.id}
                    onClick={() => openRestaurant(restaurant)}
                    type="button"
                  >
                    <Image
                      alt={restaurant.name}
                      className="resto-img"
                      height={160}
                      src={imageSrc(restaurant.image_url)}
                      width={600}
                    />
                    <span className="resto-content">
                      <span className="resto-title">
                        {restaurant.name}
                        <span className={restaurant.is_open ? "open-badge" : "closed-badge"}>
                          {restaurant.is_open ? "Ouvert" : "Ferme"}
                        </span>
                      </span>
                      <span className="resto-desc">{restaurant.description || "Specialites culinaires"}</span>
                      <span className="resto-meta">{restaurant.address}</span>
                    </span>
                  </button>
                ))}
              </div>
            )}
          </>
        ) : (
          <>
            <button className="back-btn" onClick={closeMenu} type="button">
              ← Retour
            </button>
            <Image
              alt={selectedRestaurant.name}
              className="menu-banner"
              height={220}
              src={imageSrc(selectedRestaurant.image_url)}
              width={1000}
            />
            <div className="menu-header">
              <h1>{selectedRestaurant.name}</h1>
              <p>
                {selectedRestaurant.address} · {selectedRestaurant.phone || "Telephone non renseigne"}
              </p>
            </div>

            {loadingData ? (
              <p className="muted">Chargement du menu...</p>
            ) : (
              plats.map((plat) => {
                const quantity = quantityFor(plat.id);
                return (
                  <article className="plat-card" key={plat.id}>
                    <div className="plat-info">
                      <h2>{plat.nom}</h2>
                      <p>{plat.description || "Plat prepare par le restaurant."}</p>
                      <div className="plat-footer">
                        <span className="plat-price">{formatPrice(plat.prix)}</span>
                        {plat.is_available ? (
                          quantity === 0 ? (
                            <button className="btn-add" onClick={() => addToCart(plat)} type="button">
                              + Ajouter
                            </button>
                          ) : (
                            <span className="qty-ctrl">
                              <button className="qty-btn" onClick={() => changeQuantity(plat.id, -1)} type="button">
                                -
                              </button>
                              <span className="qty-val">{quantity}</span>
                              <button className="qty-btn" onClick={() => changeQuantity(plat.id, 1)} type="button">
                                +
                              </button>
                            </span>
                          )
                        ) : (
                          <span className="plat-unavailable">Indisponible</span>
                        )}
                      </div>
                    </div>
                    <Image
                      alt={plat.nom}
                      className={`plat-img ${plat.is_available ? "" : "disabled"}`}
                      height={100}
                      src={imageSrc(plat.image_url)}
                      width={100}
                    />
                  </article>
                );
              })
            )}
          </>
        )}
      </section>

      <div className={`cart-overlay ${cartOpen ? "open" : ""}`} onClick={() => setCartOpen(false)} />
      <aside className={`cart-panel ${cartOpen ? "open" : ""}`}>
        <div className="cart-header">
          <h2>Mon panier</h2>
          <button className="cart-close" onClick={() => setCartOpen(false)} type="button">
            x
          </button>
        </div>
        {selectedRestaurant && cart.length > 0 && (
          <div className="cart-resto-label">{selectedRestaurant.name}</div>
        )}
        <div className="cart-items">
          {cart.length === 0 ? (
            <div className="cart-empty">
              <span className="cart-empty-icon">🛒</span>
              <p>Votre panier est vide. Ajoutez des plats pour commencer.</p>
            </div>
          ) : (
            cart.map((item) => (
              <div className="cart-item" key={item.plat.id}>
                <div className="cart-item-info">
                  <div className="cart-item-name">{item.plat.nom}</div>
                  <div className="cart-item-price">{formatPrice(item.plat.prix)} / unite</div>
                </div>
                <div className="cart-item-controls">
                  <button className="cart-item-qty-btn" onClick={() => changeQuantity(item.plat.id, -1)} type="button">
                    -
                  </button>
                  <span className="cart-item-qty">{item.quantite}</span>
                  <button className="cart-item-qty-btn" onClick={() => changeQuantity(item.plat.id, 1)} type="button">
                    +
                  </button>
                </div>
                <div className="cart-item-total">{formatPrice(item.plat.prix * item.quantite)}</div>
              </div>
            ))
          )}
        </div>
        {cart.length > 0 && (
          <div className="cart-footer">
            <div className="cart-summary">
              <span>Total</span>
              <strong>{formatPrice(cartTotal)}</strong>
            </div>
            <button className="btn-checkout" onClick={submitOrder} type="button">
              Commander →
            </button>
          </div>
        )}
      </aside>

      {confirmedOrder && selectedRestaurant && (
        <div className="confirm-overlay open">
          <section className="confirm-box">
            <span className="confirm-icon">✓</span>
            <h2>Commande confirmee</h2>
            <p>Votre commande a bien ete envoyee au restaurant.</p>
            <div className="confirm-detail">
              <div className="confirm-detail-row">
                <span>Commande #{confirmedOrder.id}</span>
                <span>{new Date().toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" })}</span>
              </div>
              <div className="confirm-detail-row">
                <span>Restaurant</span>
                <span>{selectedRestaurant.name}</span>
              </div>
              <div className="confirm-detail-row">
                <span>Statut</span>
                <span>En attente</span>
              </div>
              <div className="confirm-detail-row">
                <span>Total</span>
                <span>{formatPrice(confirmedOrder.prix_total)}</span>
              </div>
            </div>
            <button className="btn-confirm-close" onClick={() => setConfirmedOrder(null)} type="button">
              Parfait
            </button>
          </section>
        </div>
      )}

      {toast && <div className="toast show">{toast}</div>}
    </main>
  );
}
