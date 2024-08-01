import sys
import grpc
from random import choice

from faker import Faker
from locust import constant_pacing, task
from locust.exception import LocustError
from grpc_utils.utils import GrpcUser

sys.path.append("./proto_cyrex")

from proto_cyrex.auth_service_pb2_grpc import AuthServiceStub
from proto_cyrex.rpc_signin_user_pb2 import SignInUserInput, SignInUserResponse
from proto_cyrex.vacancy_service_pb2_grpc import VacancyServiceStub
from proto_cyrex.rpc_create_vacancy_pb2 import CreateVacancyRequest
from proto_cyrex.rpc_update_vacancy_pb2 import UpdateVacancyRequest
from proto_cyrex.vacancy_service_pb2 import VacancyRequest, GetVacanciesRequest
from proto_cyrex.vacancy_pb2 import VacancyResponse, Vacancy

from creds_load import load_credentials


USER_CREDENTIALS = load_credentials()


faker = Faker(seed=42)
division_choices = (
    Vacancy.DIVISION.DEVELOPMENT,
    Vacancy.DIVISION.SECURITY,
    Vacancy.DIVISION.SALES,
    Vacancy.DIVISION.OTHER,
)


class BaseUser(GrpcUser):
    abstract = True
    token = None
    _user_id = 0
    user_id = 0

    def on_start(self) -> None:
        self.user_id = self.user_id
        self._user_id += 1
        if USER_CREDENTIALS:
            email, password = USER_CREDENTIALS[self.user_id % len(USER_CREDENTIALS)]
            try:
                auth_service: AuthServiceStub = self.setup_stub(AuthServiceStub)
                response: SignInUserResponse = auth_service.SignInUser(
                    SignInUserInput(
                        email=email,
                        password=password,
                    )
                )
                self.token = response.access_token
            except grpc.RpcError as e:
                raise LocustError(
                    "Failed to login user with provided credentials\n" "error:\n" f"{e}"
                )
        else:
            raise LocustError("Credentials are not provided")
        return super().on_start()


class HardworkingUser(BaseUser):
    wait_time = constant_pacing(30)

    @task
    def single_vacancy_chore(self):
        vacancy_service: VacancyServiceStub = self.setup_stub(VacancyServiceStub)

        create_vacancy_response: VacancyResponse = vacancy_service.CreateVacancy(
            CreateVacancyRequest(
                Title=faker.job(),
                Description=faker.paragraph(),
                Division=choice(division_choices),
                Country=faker.country_code(),
            ),
            timeout=10,
        )
        vacancy = create_vacancy_response.vacancy

        try:
            vacancy_service.UpdateVacancy(
                UpdateVacancyRequest(
                    Id=vacancy.Id,
                    Title=faker.job(),
                    Description=faker.paragraph(),
                    Division=choice(division_choices),
                    Country=faker.country_code(),
                    Views=faker.pyint(),
                ),
                timeout=10,
            )
            vacancy_service.GetVacancy(VacancyRequest(Id=vacancy.Id), timeout=10)
        finally:
            vacancy_service.DeleteVacancy(VacancyRequest(Id=vacancy.Id), timeout=10)


class ObserverUser(GrpcUser):
    wait_time = constant_pacing(45)

    @task
    def check_all_vacancies(self):
        vacancy_service: VacancyServiceStub = self.setup_stub(VacancyServiceStub)

        vacancies = vacancy_service.GetVacancies(
            GetVacanciesRequest(
                page=1,
                limit=100,
            ),
            timeout=45,
        )

        v_plain = [v for v in vacancies]
