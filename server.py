import asyncio
import logging
import random
import sys
import uuid

sys.path.append("./proto_cyrex")

import grpc
from google.protobuf import timestamp_pb2
from proto_cyrex.vacancy_service_pb2_grpc import (
    VacancyServiceServicer,
    add_VacancyServiceServicer_to_server,
)
from proto_cyrex.vacancy_pb2 import VacancyResponse, Vacancy
from proto_cyrex.vacancy_service_pb2 import VacancyRequest, GetVacanciesRequest


division_choices = (
    Vacancy.DIVISION.DEVELOPMENT,
    Vacancy.DIVISION.SECURITY,
    Vacancy.DIVISION.SALES,
    Vacancy.DIVISION.OTHER,
)


class LocalVacancyServer(VacancyServiceServicer):
    """
    This server is only for test purposes.
    Declared only GetVacancy and GetVacancies as most simple and most complex methods.
    Feel free to extend with other methods.
    If wish to use in development then comment not implemented methods in locustfile
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

    async def GetVacancy(self, request: VacancyRequest, context):
        return VacancyResponse(vacancy=self.vacancies[0])


async def serve():
    server = grpc.aio.server()
    add_VacancyServiceServicer_to_server(LocalVacancyServer(), server)
    listen_addr = "[::]:50051"
    server.add_insecure_port(listen_addr)
    logging.info("Starting server on %s", listen_addr)

    await server.start()
    await server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(serve())
