@router.post("/auth/register")   # crée un compte, retourne un token
@router.post("/auth/login")      # vérifie email+password, retourne un token
@router.get("/auth/me")          # retourne le profil (nécessite token)