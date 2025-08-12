from fastapi import status, HTTPException


UserNotExistsException = lambda tg_id: HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail=f'User with this tg_id {tg_id} no find'
)
