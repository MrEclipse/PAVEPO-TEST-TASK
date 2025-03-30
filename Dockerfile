FROM ubuntu:latest
LABEL authors="karan"

ENTRYPOINT ["top", "-b"]