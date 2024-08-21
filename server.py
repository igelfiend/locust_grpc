import asyncio
import logging
import random
import sys
import uuid

sys.path.append("./proto_cyrex")

import grpc
from google.protobuf import timestamp_pb2

from creds_load import load_credentials
from proto_cyrex.rpc_create_vacancy_pb2 import CreateVacancyRequest
from proto_cyrex.rpc_signin_user_pb2 import SignInUserInput, SignInUserResponse
from proto_cyrex.rpc_update_vacancy_pb2 import UpdateVacancyRequest
from proto_cyrex.vacancy_service_pb2_grpc import (
    VacancyServiceServicer,
    add_VacancyServiceServicer_to_server,
)
from proto_cyrex.auth_service_pb2_grpc import (
    AuthServiceServicer,
    add_AuthServiceServicer_to_server,
)
from proto_cyrex.vacancy_pb2 import VacancyResponse, Vacancy
from proto_cyrex.vacancy_service_pb2 import (
    DeleteVacancyResponse,
    VacancyRequest,
    GetVacanciesRequest,
)


division_choices = (
    Vacancy.DIVISION.DEVELOPMENT,
    Vacancy.DIVISION.SECURITY,
    Vacancy.DIVISION.SALES,
    Vacancy.DIVISION.OTHER,
)


users = {}


def token_validator(token: str):
    token_parts = token.split()
    if (len(token_parts) != 2) or (token_parts[0].lower() != "bearer"):
        return False

    return token_parts[1] in users


class AuthInterceptor(grpc.aio.ServerInterceptor):
    def __init__(self, token_validator):
        self.token_validator = token_validator

    async def intercept_service(
        self, continuation, handler_call_details: grpc.HandlerCallDetails
    ):
        metadata = dict(handler_call_details.invocation_metadata)
        token = metadata.get("authorization")

        method_name = handler_call_details.method.split("/")[-1]
        if token or method_name not in {"SignInUser", "SignUpUser"}:
            if not self.token_validator(token):
                raise grpc.RpcError(
                    grpc.StatusCode.UNAUTHENTICATED,
                    "Invalid or missing token",
                )

        return await continuation(handler_call_details)


class AuthService(AuthServiceServicer):
    async def SignInUser(self, request: SignInUserInput, context: grpc.ServicerContext):
        """As a mock we just simulate successfull login"""
        try:
            token = next(k for k, v in users.items() if v == request.email)
            return SignInUserResponse(
                status="success",
                access_token=str(token),
                refresh_token=str(token),
            )
        except StopIteration:
            context.abort(
                code=grpc.StatusCode.NOT_FOUND,
                detail="User not found",
            )


class LocalVacancyServer(VacancyServiceServicer):
    """
    Server to run on local machine.
    Initiates with 1000 random vacancies.
    """

    vacancies_count = 1_000

    def __init__(self):
        logging.info(f"Initiating server with {self.vacancies_count} dummy vacancies")
        self.vacancies = [
            Vacancy(
                Id=str(uuid.uuid4()),
                Title=f"Title{i}",
                Description=f"Description{i}",
                Views=i,
                Division=division_choices[i % 4],
                Country=f"Country{i}",
                created_at=timestamp_pb2.Timestamp(
                    seconds=random.randint(0, 1_000_000_000),
                    nanos=random.randint(0, 1_000_000_000),
                ),
                updated_at=timestamp_pb2.Timestamp(
                    seconds=random.randint(0, 1_000_000_000),
                    nanos=random.randint(0, 1_000_000_000),
                ),
            )
            for i in range(self.vacancies_count)
        ]
        logging.info(f"Created {self.vacancies_count} dummy vacancies")

    async def GetVacancies(self, request: GetVacanciesRequest, context):
        start = (request.page - 1) * request.limit
        end = start + request.limit
        logging.info(f"requested from {start} to {end}")
        for vacancy in self.vacancies[start:end]:
            yield vacancy

    async def GetVacancy(
        self,
        request: VacancyRequest,
        context: grpc.ServicerContext,
    ):
        try:
            vacancy = next(v for v in self.vacancies if v.Id == request.Id)
            return VacancyResponse(vacancy=vacancy)
        except StopIteration:
            context.abort(
                code=grpc.StatusCode.NOT_FOUND,
                details=f"Vacancy with Id {request.Id} not found",
            )

    async def CreateVacancy(
        self,
        request: CreateVacancyRequest,
        context: grpc.ServicerContext,
    ):
        try:
            vacancy = next(v for v in self.vacancies if v.Id == request.Title)
            context.abort(
                code=grpc.StatusCode.ALREADY_EXISTS,
                details=f"post with that title already exists",
            )
        except StopIteration:
            new_vacancy = Vacancy(
                Id=str(uuid.uuid4()),
                Title=request.Title,
                Description=request.Description,
                Views=0,
                Division=request.Division,
                Country=request.Country,
                created_at=timestamp_pb2.Timestamp().GetCurrentTime(),
                updated_at=timestamp_pb2.Timestamp().GetCurrentTime(),
            )
            self.vacancies.append(new_vacancy)
            return VacancyResponse(vacancy=new_vacancy)

    async def UpdateVacancy(
        self,
        request: UpdateVacancyRequest,
        context: grpc.ServicerContext,
    ):
        try:
            vacancy = next(v for v in self.vacancies if v.Id == request.Id)
            vacancy.Title = request.Title
            vacancy.Description = request.Description
            vacancy.Views = request.Views
            vacancy.Division = request.Division
            vacancy.Country = request.Country
            vacancy.updated_at.GetCurrentTime()
            return VacancyResponse(vacancy=vacancy)
        except StopIteration:
            context.abort(
                code=grpc.StatusCode.NOT_FOUND,
                details=f"Vacancy with Id {request.Id} not found",
            )

    async def DeleteVacancy(
        self,
        request: VacancyRequest,
        context: grpc.ServicerContext,
    ):
        try:
            vacancy = next(v for v in self.vacancies if v.Id == request.Id)
            self.vacancies.remove(vacancy)
        except StopIteration:
            context.abort(
                code=grpc.StatusCode.NOT_FOUND,
                details=f"Vacancy with Id {request.Id} not found",
            )
        return DeleteVacancyResponse(success=True)


async def serve():
    creds = load_credentials()

    global users
    # saving dict with token - user info
    users = {str(uuid.uuid4()): cred[0] for cred in creds}
    logging.info(f"Users loaded: {len(creds)}")

    server = grpc.aio.server(interceptors=[AuthInterceptor(token_validator)])

    add_VacancyServiceServicer_to_server(LocalVacancyServer(), server)
    add_AuthServiceServicer_to_server(AuthService(), server)

    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)

    logging.info("Starting server on %s", listen_addr)

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
