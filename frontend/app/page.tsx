"use client";

import { FormEvent, useCallback, useEffect, useMemo, useState } from "react";
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
  owner_id?: number | null;
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
  created_at: string;
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
  const [allPlats, setAllPlats] = useState<Plat[]>([]);
  const [userOrders, setUserOrders] = useState<OrderResponse[]>([]);
  const [selectedRestaurant, setSelectedRestaurant] = useState<Restaurant | null>(null);
  const [showOrdersPage, setShowOrdersPage] = useState(false);
  const [showRestaurantAdminPage, setShowRestaurantAdminPage] = useState(false);
  const [ownerRestaurant, setOwnerRestaurant] = useState<Restaurant | null>(null);
  const [ownerPlats, setOwnerPlats] = useState<Plat[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [cartOpen, setCartOpen] = useState(false);
  const [authError, setAuthError] = useState("");
  const [authSuccess, setAuthSuccess] = useState("");
  const [loadingAuth, setLoadingAuth] = useState(false);
  const [loadingData, setLoadingData] = useState(false);
  const [loadingOrders, setLoadingOrders] = useState(false);
  const [loadingRestaurantAdmin, setLoadingRestaurantAdmin] = useState(false);
  const [loadingProfile, setLoadingProfile] = useState(false);
  const [ordersError, setOrdersError] = useState("");
  const [restaurantAdminError, setRestaurantAdminError] = useState("");
  const [profileError, setProfileError] = useState("");
  const [toast, setToast] = useState("");
  const [confirmedOrder, setConfirmedOrder] = useState<OrderResponse | null>(null);

  const authHeaders = useMemo<Record<string, string>>(() => {
    if (!token) return {} as Record<string, string>;
    return { Authorization: `Bearer ${token}` };
  }, [token]);

  const cartCount = cart.reduce((total, item) => total + item.quantite, 0);
  const cartTotal = cart.reduce((total, item) => total + item.plat.prix * item.quantite, 0);
  const ongoingOrders = userOrders.filter((order) => !["terminee", "annulee"].includes(order.statut));
  const sortedOrders = [...userOrders].sort((first, second) => {
    const firstIsOngoing = !["terminee", "annulee"].includes(first.statut);
    const secondIsOngoing = !["terminee", "annulee"].includes(second.statut);

    if (firstIsOngoing !== secondIsOngoing) return firstIsOngoing ? -1 : 1;

    return new Date(second.created_at).getTime() - new Date(first.created_at).getTime();
  });

  function notify(message: string) {
    setToast(message);
    window.setTimeout(() => setToast(""), 3000);
  }

  function restaurantName(restaurantId: number) {
    return restaurants.find((restaurant) => restaurant.id === restaurantId)?.name || `Restaurant #${restaurantId}`;
  }

  function platName(platId: number) {
    return allPlats.find((plat) => plat.id === platId)?.nom || `Plat #${platId}`;
  }

  function statusLabel(status: string) {
    const labels: Record<string, string> = {
      en_attente: "En attente",
      acceptee: "Acceptee",
      en_preparation: "En preparation",
      prete: "Prete",
      annulee: "Annulee",
      terminee: "Terminee",
    };

    return labels[status] || status;
  }

  async function loadOwnerRestaurant(force = false) {
    if (!currentUser || !token || loadingRestaurantAdmin) return;
    if (!force && ownerRestaurant) return;

    setRestaurantAdminError("");
    setLoadingRestaurantAdmin(true);

    try {
      const restaurantsResponse = await fetch(`${API_URL}/restaurants/`);
      const restaurantsData = await parseApiResponse<Restaurant[]>(restaurantsResponse);
      setRestaurants(restaurantsData);

      const ownedRestaurant = restaurantsData.find((restaurant) => restaurant.owner_id === currentUser.id) || null;
      setOwnerRestaurant(ownedRestaurant);

      if (ownedRestaurant) {
        const platsResponse = await fetch(`${API_URL}/plats/restaurant/${ownedRestaurant.id}`);
        const platsData = await parseApiResponse<Plat[]>(platsResponse);
        setOwnerPlats(platsData);
        setAllPlats((current) => {
          const otherPlats = current.filter((plat) => plat.restaurant_id !== ownedRestaurant.id);
          return [...otherPlats, ...platsData];
        });
      } else {
        setOwnerPlats([]);
      }
    } catch (error) {
      setRestaurantAdminError(error instanceof Error ? error.message : "Impossible de charger le restaurant.");
    } finally {
      setLoadingRestaurantAdmin(false);
    }
  }

  const loadUserOrders = useCallback(
    async (force = false) => {
      if (!currentUser || !token || loadingOrders) return;
      if (!force && userOrders.length > 0) return;

      setOrdersError("");
      setLoadingOrders(true);

      try {
        const [ordersResponse, platsResponse] = await Promise.all([
          fetch(`${API_URL}/commandes/user/${currentUser.id}`, {
            headers: authHeaders,
          }),
          allPlats.length === 0 ? fetch(`${API_URL}/plats/`) : Promise.resolve(null),
        ]);
        const orders = await parseApiResponse<OrderResponse[]>(ordersResponse);
        setUserOrders(orders);

        if (platsResponse) {
          const platsData = await parseApiResponse<Plat[]>(platsResponse);
          setAllPlats(platsData);
        }
      } catch (error) {
        setOrdersError(error instanceof Error ? error.message : "Impossible de charger les commandes.");
      } finally {
        setLoadingOrders(false);
      }
    },
    [allPlats.length, authHeaders, currentUser, loadingOrders, token, userOrders.length],
  );

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

  useEffect(() => {
    const timeoutId = window.setTimeout(() => loadUserOrders(), 0);

    return () => window.clearTimeout(timeoutId);
  }, [loadUserOrders]);

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

  async function handleProfileUpdate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!currentUser || !token) return;

    setProfileError("");
    setLoadingProfile(true);

    const form = new FormData(event.currentTarget);
    const payload = {
      username: String(form.get("username") || "").trim(),
      email: String(form.get("email") || "").trim(),
      phone: String(form.get("phone") || "").trim() || null,
      address: String(form.get("address") || "").trim() || null,
    };

    try {
      const response = await fetch(`${API_URL}/users/${currentUser.id}`, {
        method: "PATCH",
        headers: {
          ...authHeaders,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const updatedUser = await parseApiResponse<User>(response);
      sessionStorage.setItem("user", JSON.stringify(updatedUser));
      setCurrentUser(updatedUser);
      notify("Profil mis a jour.");
    } catch (error) {
      setProfileError(error instanceof Error ? error.message : "Modification impossible.");
    } finally {
      setLoadingProfile(false);
    }
  }

  function openOrdersPage() {
    setShowOrdersPage(true);
    setShowRestaurantAdminPage(false);
    setSelectedRestaurant(null);
    setCartOpen(false);
    loadUserOrders(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function openRestaurantAdminPage() {
    setShowRestaurantAdminPage(true);
    setShowOrdersPage(false);
    setSelectedRestaurant(null);
    setCartOpen(false);
    loadOwnerRestaurant(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function handleRestaurantSave(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!token) return;

    setRestaurantAdminError("");
    setLoadingRestaurantAdmin(true);

    const form = new FormData(event.currentTarget);
    const payload = {
      name: String(form.get("name") || "").trim(),
      address: String(form.get("address") || "").trim(),
      phone: String(form.get("phone") || "").trim() || null,
      description: String(form.get("description") || "").trim() || null,
      image_url: String(form.get("image_url") || "").trim() || null,
      is_open: form.get("is_open") === "on",
    };

    try {
      const response = await fetch(
        ownerRestaurant ? `${API_URL}/restaurants/${ownerRestaurant.id}` : `${API_URL}/restaurants/`,
        {
          method: ownerRestaurant ? "PATCH" : "POST",
          headers: {
            ...authHeaders,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(payload),
        },
      );
      const savedRestaurant = await parseApiResponse<Restaurant>(response);
      setOwnerRestaurant(savedRestaurant);
      setRestaurants((current) => {
        const withoutSaved = current.filter((restaurant) => restaurant.id !== savedRestaurant.id);
        return [...withoutSaved, savedRestaurant];
      });
      notify(ownerRestaurant ? "Restaurant mis a jour." : "Restaurant cree.");
    } catch (error) {
      setRestaurantAdminError(error instanceof Error ? error.message : "Enregistrement impossible.");
    } finally {
      setLoadingRestaurantAdmin(false);
    }
  }

  async function handleCreatePlat(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ownerRestaurant || !token) return;

    setRestaurantAdminError("");
    const form = new FormData(event.currentTarget);
    const payload = {
      nom: String(form.get("nom") || "").trim(),
      prix: Number(form.get("prix") || 0),
      description: String(form.get("description") || "").trim() || null,
      ingredients: String(form.get("ingredients") || "").trim() || null,
      allergenes: String(form.get("allergenes") || "").trim() || null,
      image_url: String(form.get("image_url") || "").trim() || null,
      is_available: form.get("is_available") === "on",
      restaurant_id: ownerRestaurant.id,
    };

    try {
      const response = await fetch(`${API_URL}/plats/`, {
        method: "POST",
        headers: {
          ...authHeaders,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const createdPlat = await parseApiResponse<Plat>(response);
      setOwnerPlats((current) => [...current, createdPlat]);
      setAllPlats((current) => [...current.filter((plat) => plat.id !== createdPlat.id), createdPlat]);
      event.currentTarget.reset();
      notify("Plat ajoute.");
    } catch (error) {
      setRestaurantAdminError(error instanceof Error ? error.message : "Creation du plat impossible.");
    }
  }

  async function handleUpdatePlat(platId: number, event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!ownerRestaurant || !token) return;

    setRestaurantAdminError("");
    const form = new FormData(event.currentTarget);
    const payload = {
      nom: String(form.get("nom") || "").trim(),
      prix: Number(form.get("prix") || 0),
      description: String(form.get("description") || "").trim() || null,
      ingredients: String(form.get("ingredients") || "").trim() || null,
      allergenes: String(form.get("allergenes") || "").trim() || null,
      image_url: String(form.get("image_url") || "").trim() || null,
      is_available: form.get("is_available") === "on",
      restaurant_id: ownerRestaurant.id,
    };

    try {
      const response = await fetch(`${API_URL}/plats/${platId}`, {
        method: "PATCH",
        headers: {
          ...authHeaders,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      const updatedPlat = await parseApiResponse<Plat>(response);
      setOwnerPlats((current) => current.map((plat) => (plat.id === updatedPlat.id ? updatedPlat : plat)));
      setAllPlats((current) => [...current.filter((plat) => plat.id !== updatedPlat.id), updatedPlat]);
      notify("Plat mis a jour.");
    } catch (error) {
      setRestaurantAdminError(error instanceof Error ? error.message : "Modification du plat impossible.");
    }
  }

  async function openRestaurant(restaurant: Restaurant) {
    setShowRestaurantAdminPage(false);
    setShowOrdersPage(false);
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
    setShowRestaurantAdminPage(false);
    setShowOrdersPage(false);
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
      setUserOrders((current) => [order, ...current.filter((item) => item.id !== order.id)]);
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
    setAllPlats([]);
    setUserOrders([]);
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
          <div className="user-menu">
            <button className="user-badge" type="button">
              <span className="user-avatar">{currentUser.username.slice(0, 2).toUpperCase()}</span>
              <span>{currentUser.username}</span>
            </button>
            <div className="profile-dropdown">
              <div className="profile-dropdown-header">
                <strong>Profil</strong>
                <span>{currentUser.email}</span>
              </div>
              <form className="profile-form" onSubmit={handleProfileUpdate}>
                {profileError && <div className="profile-error">{profileError}</div>}
                <label>
                  Nom d&apos;utilisateur
                  <input name="username" defaultValue={currentUser.username} required />
                </label>
                <label>
                  Email
                  <input name="email" defaultValue={currentUser.email} type="email" required />
                </label>
                <label>
                  Telephone
                  <input name="phone" defaultValue={currentUser.phone || ""} />
                </label>
                <label>
                  Adresse
                  <input name="address" defaultValue={currentUser.address || ""} />
                </label>
                <button className="profile-save" disabled={loadingProfile} type="submit">
                  {loadingProfile ? "Enregistrement..." : "Enregistrer"}
                </button>
              </form>
            </div>
          </div>
          <div className="restaurant-menu" onFocus={() => loadOwnerRestaurant()} onMouseEnter={() => loadOwnerRestaurant()}>
            <button className="restaurant-btn" onClick={openRestaurantAdminPage} type="button">
              Mon restaurant
            </button>
            <div className="restaurant-dropdown">
              <div className="orders-dropdown-header">
                <strong>Restaurant</strong>
                <button onClick={() => loadOwnerRestaurant(true)} type="button">
                  Actualiser
                </button>
              </div>
              {restaurantAdminError && <div className="profile-error">{restaurantAdminError}</div>}
              {loadingRestaurantAdmin ? (
                <p className="orders-muted">Chargement...</p>
              ) : ownerRestaurant ? (
                <div className="restaurant-dropdown-card">
                  <strong>{ownerRestaurant.name}</strong>
                  <span>{ownerRestaurant.address}</span>
                  <span className={ownerRestaurant.is_open ? "open-badge" : "closed-badge"}>
                    {ownerRestaurant.is_open ? "Ouvert" : "Ferme"}
                  </span>
                  <button onClick={openRestaurantAdminPage} type="button">
                    Modifier restaurant et plats
                  </button>
                </div>
              ) : (
                <div className="restaurant-dropdown-card">
                  <strong>Aucun restaurant</strong>
                  <span>Creez votre fiche restaurant pour ajouter vos plats.</span>
                  <button onClick={openRestaurantAdminPage} type="button">
                    Creer un restaurant
                  </button>
                </div>
              )}
            </div>
          </div>
          <div className="orders-menu" onFocus={() => loadUserOrders()} onMouseEnter={() => loadUserOrders()}>
            <button className="orders-btn" onClick={openOrdersPage} type="button">
              {ongoingOrders.length} commande{ongoingOrders.length > 1 ? "s" : ""} en cours
            </button>
            <div className="orders-dropdown">
              <div className="orders-dropdown-header">
                <strong>Mes commandes</strong>
                <button onClick={() => loadUserOrders(true)} type="button">
                  Actualiser
                </button>
              </div>
              {ordersError && <div className="profile-error">{ordersError}</div>}
              {loadingOrders ? (
                <p className="orders-muted">Chargement...</p>
              ) : sortedOrders.length === 0 ? (
                <p className="orders-muted">Aucune commande pour le moment.</p>
              ) : (
                <div className="orders-list">
                  {sortedOrders.map((order) => {
                    const isOngoing = !["terminee", "annulee"].includes(order.statut);

                    return (
                    <article className={`order-card ${isOngoing ? "ongoing" : ""}`} key={order.id}>
                      <div className="order-card-top">
                        <strong>Commande #{order.id}</strong>
                        <span>{formatPrice(order.prix_total)}</span>
                      </div>
                      <div className="order-card-meta">
                        <span>{restaurantName(order.restaurant_id)}</span>
                        <span>{new Date(order.created_at).toLocaleDateString("fr-FR")}</span>
                      </div>
                      <div className="order-card-status">{statusLabel(order.statut)}</div>
                      <ul className="order-items">
                        {order.items.map((item) => (
                          <li key={`${order.id}-${item.plat_id}`}>
                            <span>{platName(item.plat_id)}</span>
                            <strong>x{item.quantite}</strong>
                          </li>
                        ))}
                      </ul>
                    </article>
                    );
                  })}
                </div>
              )}
            </div>
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
        {showRestaurantAdminPage ? (
          <>
            <button className="back-btn" onClick={closeMenu} type="button">
              ← Retour aux restaurants
            </button>
            <div className="restaurant-admin-header">
              <div>
                <div className="section-title">Mon restaurant</div>
                <div className="section-subtitle">
                  Creez ou modifiez votre restaurant, puis gerez les plats proposes.
                </div>
              </div>
              <button className="orders-refresh-main" onClick={() => loadOwnerRestaurant(true)} type="button">
                Actualiser
              </button>
            </div>
            {restaurantAdminError && <div className="profile-error admin-error">{restaurantAdminError}</div>}
            <section className="restaurant-admin-grid">
              <form
                className="admin-panel admin-form"
                key={ownerRestaurant?.id || "new-restaurant"}
                onSubmit={handleRestaurantSave}
              >
                <h2>{ownerRestaurant ? "Modifier le restaurant" : "Creer un restaurant"}</h2>
                <label>
                  Nom
                  <input name="name" defaultValue={ownerRestaurant?.name || ""} required />
                </label>
                <label>
                  Adresse
                  <input name="address" defaultValue={ownerRestaurant?.address || ""} required />
                </label>
                <label>
                  Telephone
                  <input name="phone" defaultValue={ownerRestaurant?.phone || ""} />
                </label>
                <label>
                  Description
                  <textarea name="description" defaultValue={ownerRestaurant?.description || ""} rows={3} />
                </label>
                <label>
                  Image
                  <input name="image_url" defaultValue={ownerRestaurant?.image_url || ""} placeholder="/images/pizza_algo.jpg" />
                </label>
                <label className="admin-checkbox">
                  <input name="is_open" defaultChecked={ownerRestaurant?.is_open ?? true} type="checkbox" />
                  Restaurant ouvert
                </label>
                <button className="profile-save" disabled={loadingRestaurantAdmin} type="submit">
                  {loadingRestaurantAdmin ? "Enregistrement..." : ownerRestaurant ? "Enregistrer" : "Creer"}
                </button>
              </form>

              <div className="admin-panel">
                <h2>Ajouter un plat</h2>
                {!ownerRestaurant ? (
                  <p className="orders-muted">Creez d&apos;abord un restaurant pour ajouter des plats.</p>
                ) : (
                  <form className="admin-form" onSubmit={handleCreatePlat}>
                    <label>
                      Nom
                      <input name="nom" required />
                    </label>
                    <label>
                      Prix
                      <input min="0" name="prix" required step="0.01" type="number" />
                    </label>
                    <label>
                      Description
                      <textarea name="description" rows={2} />
                    </label>
                    <label>
                      Ingredients
                      <input name="ingredients" />
                    </label>
                    <label>
                      Allergenes
                      <input name="allergenes" />
                    </label>
                    <label>
                      Image
                      <input name="image_url" placeholder="/images/burger.jpg" />
                    </label>
                    <label className="admin-checkbox">
                      <input name="is_available" defaultChecked type="checkbox" />
                      Disponible
                    </label>
                    <button className="profile-save" type="submit">
                      Ajouter le plat
                    </button>
                  </form>
                )}
              </div>
            </section>

            {ownerRestaurant && (
              <section className="admin-panel plats-admin-panel">
                <h2>Plats du restaurant</h2>
                {ownerPlats.length === 0 ? (
                  <p className="orders-muted">Aucun plat pour le moment.</p>
                ) : (
                  <div className="plats-admin-list">
                    {ownerPlats.map((plat) => (
                      <form
                        className="plat-admin-card"
                        key={plat.id}
                        onSubmit={(event) => handleUpdatePlat(plat.id, event)}
                      >
                        <Image alt={plat.nom} className="plat-admin-img" height={88} src={imageSrc(plat.image_url)} width={88} />
                        <div className="plat-admin-fields">
                          <label>
                            Nom
                            <input name="nom" defaultValue={plat.nom} required />
                          </label>
                          <label>
                            Prix
                            <input min="0" name="prix" defaultValue={plat.prix} required step="0.01" type="number" />
                          </label>
                          <label>
                            Description
                            <input name="description" defaultValue={plat.description || ""} />
                          </label>
                          <label>
                            Ingredients
                            <input name="ingredients" defaultValue={plat.ingredients || ""} />
                          </label>
                          <label>
                            Allergenes
                            <input name="allergenes" defaultValue={plat.allergenes || ""} />
                          </label>
                          <label>
                            Image
                            <input name="image_url" defaultValue={plat.image_url || ""} />
                          </label>
                          <label className="admin-checkbox">
                            <input name="is_available" defaultChecked={plat.is_available} type="checkbox" />
                            Disponible
                          </label>
                          <button className="profile-save" type="submit">
                            Enregistrer ce plat
                          </button>
                        </div>
                      </form>
                    ))}
                  </div>
                )}
              </section>
            )}
          </>
        ) : showOrdersPage ? (
          <>
            <button className="back-btn" onClick={closeMenu} type="button">
              ← Retour aux restaurants
            </button>
            <div className="orders-page-header">
              <div>
                <div className="section-title">Mes commandes</div>
                <div className="section-subtitle">
                  {ongoingOrders.length} commande{ongoingOrders.length > 1 ? "s" : ""} en cours
                </div>
              </div>
              <button className="orders-refresh-main" onClick={() => loadUserOrders(true)} type="button">
                Actualiser
              </button>
            </div>
            {ordersError && <div className="profile-error">{ordersError}</div>}
            {loadingOrders ? (
              <p className="muted">Chargement des commandes...</p>
            ) : sortedOrders.length === 0 ? (
              <div className="orders-empty-state">
                <h2>Aucune commande</h2>
                <p>Vos futures commandes apparaitront ici.</p>
              </div>
            ) : (
              <div className="orders-page-list">
                {sortedOrders.map((order) => {
                  const isOngoing = !["terminee", "annulee"].includes(order.statut);

                  return (
                    <article className={`orders-page-card ${isOngoing ? "ongoing" : ""}`} key={order.id}>
                      <div className="orders-page-card-main">
                        <div>
                          <div className="orders-page-title">
                            Commande #{order.id}
                            {isOngoing && <span>En cours</span>}
                          </div>
                          <div className="order-card-meta">
                            <span>{restaurantName(order.restaurant_id)}</span>
                            <span>
                              {new Date(order.created_at).toLocaleDateString("fr-FR")} ·{" "}
                              {new Date(order.created_at).toLocaleTimeString("fr-FR", {
                                hour: "2-digit",
                                minute: "2-digit",
                              })}
                            </span>
                          </div>
                        </div>
                        <strong>{formatPrice(order.prix_total)}</strong>
                      </div>
                      <div className="order-card-status">{statusLabel(order.statut)}</div>
                      <ul className="order-items page">
                        {order.items.map((item) => (
                          <li key={`${order.id}-${item.plat_id}`}>
                            <span>{platName(item.plat_id)}</span>
                            <strong>x{item.quantite}</strong>
                          </li>
                        ))}
                      </ul>
                    </article>
                  );
                })}
              </div>
            )}
          </>
        ) : !selectedRestaurant ? (
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
