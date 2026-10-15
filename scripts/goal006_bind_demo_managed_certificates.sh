#!/usr/bin/env bash
set -euo pipefail

target_environment=${1:?Usage: goal006_bind_demo_managed_certificates.sh ENVIRONMENT RESOURCE_GROUP CONTAINER_APP_ENVIRONMENT}
resource_group=${2:?Usage: goal006_bind_demo_managed_certificates.sh ENVIRONMENT RESOURCE_GROUP CONTAINER_APP_ENVIRONMENT}
container_app_environment=${3:?Usage: goal006_bind_demo_managed_certificates.sh ENVIRONMENT RESOURCE_GROUP CONTAINER_APP_ENVIRONMENT}

if [[ "$target_environment" != "demo" ]]; then
  echo "Azure-managed Demo certificate binding is not applicable to $target_environment"
  exit 0
fi

max_attempts=${MANAGED_CERTIFICATE_MAX_ATTEMPTS:-120}
retry_interval_seconds=${MANAGED_CERTIFICATE_RETRY_INTERVAL_SECONDS:-10}
[[ "$max_attempts" =~ ^[1-9][0-9]*$ ]]
[[ "$retry_interval_seconds" =~ ^[0-9]+$ ]]

domains=(
  "ca-demo-web|cp.demo.waooaw.com"
  "ca-demo-business-platform|api.demo.waooaw.com"
  "ca-demo-identity-edge|auth.demo.waooaw.com"
)

binding_type() {
  local app_name=$1
  local hostname=$2
  az containerapp show \
    --resource-group "$resource_group" \
    --name "$app_name" \
    --query "properties.configuration.ingress.customDomains[?name=='$hostname'] | [0].bindingType" \
    --output tsv
}

for domain in "${domains[@]}"; do
  IFS="|" read -r app_name hostname <<< "$domain"
  if [[ "$(binding_type "$app_name" "$hostname")" == "SniEnabled" ]]; then
    echo "Azure-managed TLS is already bound: app=$app_name hostname=$hostname"
    continue
  fi

  echo "Finding or creating Azure-managed TLS and binding it: app=$app_name hostname=$hostname"
  az containerapp hostname bind \
    --resource-group "$resource_group" \
    --name "$app_name" \
    --hostname "$hostname" \
    --environment "$container_app_environment" \
    --validation-method CNAME \
    --only-show-errors \
    --output none
done

for attempt in $(seq 1 "$max_attempts"); do
  all_bound=true
  for domain in "${domains[@]}"; do
    IFS="|" read -r app_name hostname <<< "$domain"
    current_binding=$(binding_type "$app_name" "$hostname")
    if [[ "$current_binding" != "SniEnabled" ]]; then
      all_bound=false
      echo "Managed TLS not ready: app=$app_name hostname=$hostname binding=${current_binding:-missing} attempt=$attempt/$max_attempts"
    fi
  done

  if [[ "$all_bound" == "true" ]]; then
    echo "All Demo custom domains have Azure-managed SNI certificates"
    exit 0
  fi
  [[ "$attempt" == "$max_attempts" ]] || sleep "$retry_interval_seconds"
done

az containerapp env certificate list \
  --resource-group "$resource_group" \
  --name "$container_app_environment" \
  --managed-certificates-only \
  --query "[].{name:name,subjectName:properties.subjectName,provisioningState:properties.provisioningState}" \
  --output jsonc >&2
echo "Azure-managed Demo certificate binding did not converge" >&2
exit 1
