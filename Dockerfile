# Hardened runtime for the CHANGELOG generator.
#
# The tool parses untrusted commit messages, so the image keeps that work
# isolated: no build-time network install, no root user, no bytecode writes.
# docker-compose.yml additionally drops all capabilities, denies new
# privileges, removes networking and makes the root filesystem read-only.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/changelog-skill

# git is required only for --repo; --input/stdin need no external binary.
RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Dedicated unprivileged user with no home directory and no login shell.
RUN groupadd --gid 10001 changelog \
    && useradd --uid 10001 --gid changelog --no-create-home \
       --shell /usr/sbin/nologin changelog

WORKDIR /work
COPY changelog_skill/ /opt/changelog-skill/changelog_skill/

USER 10001:10001
ENTRYPOINT ["python", "-m", "changelog_skill"]
CMD ["--help"]
