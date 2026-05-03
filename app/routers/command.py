from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.command import CommandeCreate, CommandeLivraisonStatusUpdate, CommandeUpdate, CommandeResponse
from app.schemas.livreur import LivreurResponse
from app.crud import command as commande_crud
from app.crud import livreur as livreur_crud
from app.crud import user as user_crud
from app.crud import restaurant as restaurant_crud
from app.security import ROLE_ADMIN, check_restaurant_owner_or_admin, check_user_is_self_or_admin, get_current_user, require_roles


router = APIRouter(
    prefix="/commandes",
    tags=["Commandes"]
)


def format_commande_response(commande):
    return CommandeResponse(
        id=commande.id,
        user_id=commande.user_id,
        restaurant_id=commande.restaurant_id,
        livreur_id=commande.livreur_id,
        statut=commande.statut,
        statut_livraison=commande.statut_livraison,
        prix_total=commande.prix_total,
        created_at=commande.created_at,
        plat_ids=[plat.id for plat in commande.plats]
    )


def check_commande_access(commande, current_user):
    if current_user.role == ROLE_ADMIN or commande.user_id == current_user.id or is_assigned_livreur(commande, current_user):
        return

    check_restaurant_owner_or_admin(commande.restaurant, current_user)


def check_commande_delete_access(commande, current_user):
    if current_user.role == ROLE_ADMIN:
        return

    if commande.user_id == current_user.id and commande.statut == "en_attente":
        return

    if commande.restaurant.owner_id == current_user.id and commande.statut in ["en_attente", "en_preparation"]:
        return

    if is_assigned_livreur(commande, current_user) and commande.statut_livraison in ["assignee", "recuperee"]:
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès interdit"
    )


def is_assigned_livreur(commande, current_user):
    return commande.livreur is not None and commande.livreur.user_id == current_user.id


def check_livreur_or_admin(commande, current_user):
    if current_user.role == ROLE_ADMIN or is_assigned_livreur(commande, current_user):
        return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Accès interdit"
    )


def get_current_livreur(db: Session, current_user):
    livreur = livreur_crud.get_livreur_by_user(db, current_user.id)

    if livreur is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Profil livreur requis"
        )

    return livreur


def check_commande_available_for_delivery(commande):
    if commande.statut not in ["en_preparation", "prete"] or commande.statut_livraison != "non_assignee" or commande.livreur_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Commande non disponible pour livraison"
        )


def check_livraison_transition(current_status: str, next_status: str):
    allowed_transitions = {
        "assignee": ["recuperee"],
        "recuperee": ["en_route"],
        "en_route": ["livree"]
    }

    if next_status not in allowed_transitions.get(current_status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transition de livraison invalide"
        )


def check_commande_status_transition(current_status: str, next_status: str):
    allowed_transitions = {
        "en_attente": ["acceptee", "en_preparation", "annulee"],
        "acceptee": ["en_preparation", "annulee"],
        "en_preparation": ["prete", "annulee"],
        "prete": ["annulee"]
    }

    if next_status not in allowed_transitions.get(current_status, []):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Transition de commande invalide"
        )


def validate_commande_data(
    db: Session,
    user_id: int,
    restaurant_id: int,
    plat_ids: List[int]
):
    user = user_crud.get_user(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    restaurant = restaurant_crud.get_restaurant(db, restaurant_id)

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant introuvable"
        )

    plats = commande_crud.get_plats_by_ids(db, plat_ids)

    if len(plats) != len(set(plat_ids)):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Un ou plusieurs plats sont introuvables"
        )

    for plat in plats:
        if plat.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tous les plats doivent appartenir au restaurant de la commande"
            )

    return plats


@router.post("/", response_model=CommandeResponse, status_code=status.HTTP_201_CREATED)
def create_commande(commande: CommandeCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    check_user_is_self_or_admin(commande.user_id, current_user)

    validate_commande_data(
        db,
        commande.user_id,
        commande.restaurant_id,
        commande.plat_ids
    )

    db_commande = commande_crud.create_commande(db, commande)

    return format_commande_response(db_commande)


@router.get("/", response_model=List[CommandeResponse])
def get_commandes(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(require_roles(ROLE_ADMIN))):
    commandes = commande_crud.get_commandes(db, skip=skip, limit=limit)

    return [format_commande_response(commande) for commande in commandes]


@router.get("/available-for-delivery", response_model=List[CommandeResponse])
def get_commandes_available_for_delivery(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    get_current_livreur(db, current_user)

    commandes = commande_crud.get_commandes_available_for_delivery(db, skip=skip, limit=limit)

    return [format_commande_response(commande) for commande in commandes]


@router.get("/user/{user_id}", response_model=List[CommandeResponse])
def get_commandes_by_user(user_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    check_user_is_self_or_admin(user_id, current_user)

    user = user_crud.get_user(db, user_id)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Utilisateur introuvable"
        )

    commandes = commande_crud.get_commandes_by_user(
        db,
        user_id,
        skip=skip,
        limit=limit
    )

    return [format_commande_response(commande) for commande in commandes]


@router.get("/restaurant/{restaurant_id}", response_model=List[CommandeResponse])
def get_commandes_by_restaurant(restaurant_id: int, skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    restaurant = restaurant_crud.get_restaurant(db, restaurant_id)

    if restaurant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Restaurant introuvable"
        )

    check_restaurant_owner_or_admin(restaurant, current_user)

    commandes = commande_crud.get_commandes_by_restaurant(
        db,
        restaurant_id,
        skip=skip,
        limit=limit
    )

    return [format_commande_response(commande) for commande in commandes]


@router.get("/{commande_id}/livreur", response_model=LivreurResponse)
def get_livreur_by_commande(commande_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )

    check_commande_access(db_commande, current_user)

    if db_commande.livreur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun livreur assigné à cette commande"
        )

    return db_commande.livreur

@router.get("/{commande_id}", response_model=CommandeResponse)
def get_commande(commande_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )

    check_commande_access(db_commande, current_user)

    return format_commande_response(db_commande)


@router.patch("/{commande_id}/livraison-status", response_model=CommandeResponse)
def update_livraison_status(commande_id: int, livraison_update: CommandeLivraisonStatusUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )

    check_livreur_or_admin(db_commande, current_user)
    check_livraison_transition(db_commande.statut_livraison, livraison_update.statut_livraison)

    updated_commande = commande_crud.update_livraison_status(db, db_commande, livraison_update.statut_livraison)

    return format_commande_response(updated_commande)


@router.patch("/{commande_id}/claim-delivery", response_model=CommandeResponse)
def claim_commande_delivery(commande_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    livreur = get_current_livreur(db, current_user)

    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )

    check_commande_available_for_delivery(db_commande)

    updated_commande = commande_crud.claim_commande_delivery(db, db_commande, livreur.id)

    return format_commande_response(updated_commande)


@router.patch("/{commande_id}", response_model=CommandeResponse)
def update_commande(commande_id: int, commande_update: CommandeUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )

    check_restaurant_owner_or_admin(db_commande.restaurant, current_user)

    if commande_update.statut is not None:
        check_commande_status_transition(db_commande.statut, commande_update.statut)

    if commande_update.plat_ids is not None:
        validate_commande_data(
            db,
            db_commande.user_id,
            db_commande.restaurant_id,
            commande_update.plat_ids
        )

    updated_commande = commande_crud.update_commande(
        db,
        db_commande,
        commande_update
    )

    return format_commande_response(updated_commande)


@router.delete("/{commande_id}", response_model=CommandeResponse)
def delete_commande(commande_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    db_commande = commande_crud.get_commande(db, commande_id)

    if db_commande is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Commande introuvable"
        )

    check_commande_delete_access(db_commande, current_user)

    response = format_commande_response(db_commande)

    commande_crud.delete_commande(db, db_commande)

    return response
