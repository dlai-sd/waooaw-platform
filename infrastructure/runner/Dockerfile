FROM ghcr.io/actions/actions-runner@sha256:db0dcae6d28559e54277755a33aba7d0665f255b3bd2a66cdc5e132712f155e0

ARG AZURE_CLI_VERSION=2.79.0-1~jammy
ARG AZURE_CLI_SHA256=822502a67ea7eb8d0fe70c847c7952f88408e82d912ef7b2b11d170962799eae
ARG TERRAFORM_VERSION=1.9.8
ARG TERRAFORM_SHA256=186e0145f5e5f2eb97cbd785bc78f21bae4ef15119349f6ad4fa535b83b10df8

USER root

RUN apt-get update \
  && apt-get upgrade -y \
    && apt-get install -y --no-install-recommends ca-certificates dnsutils jq openssl unzip \
    && curl --fail --location --silent --show-error \
      --output /tmp/azure-cli.deb \
      "https://packages.microsoft.com/repos/azure-cli/pool/main/a/azure-cli/azure-cli_${AZURE_CLI_VERSION}_amd64.deb" \
    && echo "${AZURE_CLI_SHA256}  /tmp/azure-cli.deb" | sha256sum --check --strict \
    && apt-get install -y --no-install-recommends /tmp/azure-cli.deb \
    && curl --fail --location --silent --show-error \
      --output /tmp/terraform.zip \
      "https://releases.hashicorp.com/terraform/${TERRAFORM_VERSION}/terraform_${TERRAFORM_VERSION}_linux_amd64.zip" \
    && echo "${TERRAFORM_SHA256}  /tmp/terraform.zip" | sha256sum --check --strict \
    && unzip /tmp/terraform.zip -d /usr/local/bin \
    && rm -rf /var/lib/apt/lists/* /tmp/azure-cli.deb /tmp/terraform.zip

COPY --chown=runner:runner scripts/goal006_runner_lifecycle.py /opt/waooaw/goal006_runner_lifecycle.py
COPY --chown=runner:runner architecture/reference/pipeline/github-runner-app-manifest.json /opt/waooaw/github-runner-app-manifest.json
COPY --chown=runner:runner infrastructure/runner/entrypoint.sh /opt/waooaw/entrypoint.sh
COPY --chown=runner:runner infrastructure/runner/import-app-signing-material.sh /opt/waooaw/import-app-signing-material.sh
RUN chmod 0555 /opt/waooaw/entrypoint.sh /opt/waooaw/goal006_runner_lifecycle.py /opt/waooaw/import-app-signing-material.sh

USER runner
WORKDIR /home/runner
ENTRYPOINT ["/opt/waooaw/entrypoint.sh"]