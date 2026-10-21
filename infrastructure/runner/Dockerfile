FROM ghcr.io/actions/actions-runner@sha256:a1919047b038c38871d667c58cfdc7a878452711ab1212fb6036188f27a7ab16

ARG AZURE_CLI_VERSION=2.79.0-1~jammy
ARG AZURE_CLI_SHA256=822502a67ea7eb8d0fe70c847c7952f88408e82d912ef7b2b11d170962799eae
ARG TERRAFORM_VERSION=1.9.8
ARG TERRAFORM_SHA256=186e0145f5e5f2eb97cbd785bc78f21bae4ef15119349f6ad4fa535b83b10df8
# Azure CLI extensions the deployment workflow depends on. Without these pins az installs the
# newest release on first use in every job (~20 s each and a floating dependency); --system
# places them where the unprivileged runner user can load them.
ARG AZ_CONTAINERAPP_EXTENSION_VERSION=1.2.0b5
ARG AZ_LOG_ANALYTICS_EXTENSION_VERSION=1.0.0b3
ARG APT_ACQUIRE_RETRIES=5

USER root

RUN apt-get -o Acquire::Retries="${APT_ACQUIRE_RETRIES}" update \
  && apt-get -o Acquire::Retries="${APT_ACQUIRE_RETRIES}" upgrade -y \
    && apt-get -o Acquire::Retries="${APT_ACQUIRE_RETRIES}" install -y --no-install-recommends ca-certificates dnsutils jq openssl postgresql-client unzip \
    && curl --fail --location --silent --show-error \
      --output /tmp/azure-cli.deb \
      "https://packages.microsoft.com/repos/azure-cli/pool/main/a/azure-cli/azure-cli_${AZURE_CLI_VERSION}_amd64.deb" \
    && echo "${AZURE_CLI_SHA256}  /tmp/azure-cli.deb" | sha256sum --check --strict \
    && apt-get -o Acquire::Retries="${APT_ACQUIRE_RETRIES}" install -y --no-install-recommends /tmp/azure-cli.deb \
    && curl --fail --location --silent --show-error \
      --output /tmp/terraform.zip \
      "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && echo "${TERRAFORM_SHA256}  /tmp/terraform.zip" | sha256sum --check --strict \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && az extension add --name containerapp --version "${AZ_CONTAINERAPP_EXTENSION_VERSION}" --system \
    && az extension add --name log-analytics --version "${AZ_LOG_ANALYTICS_EXTENSION_VERSION}" --system \
    && rm -rf /var/lib/apt/lists/* /tmp/azure-cli.deb /tmp/terraform.zip

COPY --chown=runner:runner scripts/goal006_runner_lifecycle.py /opt/waooaw/goal006_runner_lifecycle.py
COPY --chown=runner:runner scripts/cli_errors.py /opt/waooaw/cli_errors.py
COPY --chown=runner:runner scripts/wc124_db_provisioner.py /opt/waooaw/wc124_db_provisioner.py
COPY --chown=runner:runner scripts/wc124_db_handoff.py /opt/waooaw/wc124_db_handoff.py
COPY --chown=runner:runner infrastructure/environment-readiness/secret-catalog.json /opt/waooaw/secret-catalog.json
COPY --chown=runner:runner infrastructure/postgres/init /opt/waooaw/postgres/init
COPY --chown=runner:runner architecture/reference/pipeline/github-runner-app-manifest.json /opt/waooaw/github-runner-app-manifest.json
COPY --chown=runner:runner infrastructure/runner/entrypoint.sh /opt/waooaw/entrypoint.sh
COPY --chown=runner:runner infrastructure/runner/import-app-signing-material.sh /opt/waooaw/import-app-signing-material.sh
RUN chmod 0555 /opt/waooaw/entrypoint.sh /opt/waooaw/goal006_runner_lifecycle.py /opt/waooaw/wc124_db_provisioner.py /opt/waooaw/wc124_db_handoff.py /opt/waooaw/import-app-signing-material.sh

USER runner
WORKDIR /home/runner
ENTRYPOINT ["/opt/waooaw/entrypoint.sh"]