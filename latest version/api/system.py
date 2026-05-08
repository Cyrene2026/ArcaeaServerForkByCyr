from typing import Any

from fastapi import APIRouter, Depends

from core.api_user import APIUser
from core.error import ArcError
from core.operation import BaseOperation

from .native import api_success, require_api_user

router = APIRouter(prefix='/system', tags=['system'])

operation_dict = {i._name: i for i in BaseOperation.__subclasses__()}


@router.get('/operations')
def operations_get(user: APIUser = Depends(require_api_user(['system']))):
    return api_success(list(operation_dict.keys()))


@router.post('/operations/{operation_name}')
def operations_operation_post(
    operation_name: str,
    data: dict[str, Any],
    user: APIUser = Depends(require_api_user(['system'])),
):
    if operation_name not in operation_dict:
        raise ArcError(
            f'No such operation: `{operation_name}`', api_error_code=-1, status=404)
    x = operation_dict[operation_name]()
    x.set_params(**data)
    x.run()
    return api_success()
