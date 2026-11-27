FROM mysql:8.0
WORKDIR /mysql/data
ENV MYSQL_ROOT_PASSWORD=datarea
COPY database_dwolist.sql /docker-entrypoint-initdb.d/
