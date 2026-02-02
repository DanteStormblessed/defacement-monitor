param(
  [string]$ResourceGroup = "monitor",
  [string]$Location = "chilecentral",
  [string]$AksName = "defacementmonitor-aks",
  [string]$AcrName = "defacementmonitoracr",
  [string]$ImageTag = "0.1.0",
  [string]$Namespace = "default"
)

$ErrorActionPreference = "Stop"

Write-Host "== Providers status (may take time) =="
$providers = @(
  "Microsoft.ContainerService",
  "Microsoft.Network",
  "Microsoft.Compute",
  "Microsoft.OperationalInsights",
  "Microsoft.ContainerRegistry"
)
foreach ($p in $providers) {
  try {
    $state = az provider show --namespace $p --query "registrationState" -o tsv
    Write-Host "$p : $state"
  } catch {
    Write-Host "$p : (unable to query)"
  }
}

Write-Host "== Create AKS (if not exists) =="
$aksExists = az aks show -g $ResourceGroup -n $AksName --query "name" -o tsv 2>$null
if (-not $aksExists) {
  az aks create -g $ResourceGroup -n $AksName --location $Location --enable-managed-identity --node-count 2
}

Write-Host "== Attach ACR to AKS =="
az aks update -g $ResourceGroup -n $AksName --attach-acr $AcrName

Write-Host "== Get kubectl credentials =="
az aks get-credentials -g $ResourceGroup -n $AksName --overwrite-existing

Write-Host "== Build & push image to ACR =="
# Run from repo root when executing this script.
# Note: ACR Tasks (az acr build) isn't available in all regions (e.g., chilecentral).
try {
  az acr build -r $AcrName -t "target-manager:$ImageTag" -f target-manager/Dockerfile .
} catch {
  Write-Host "az acr build failed. This is commonly due to ACR Tasks not being supported in the registry region." -ForegroundColor Yellow
  Write-Host "Falling back to local docker build + push (requires Docker Desktop)." -ForegroundColor Yellow

  $docker = Get-Command docker -ErrorAction SilentlyContinue
  if (-not $docker) {
    throw "Docker is not installed. Either install Docker Desktop or create a new ACR in a supported region and use az acr build."
  }

  $loginServer = az acr show -n $AcrName -g $ResourceGroup --query loginServer -o tsv
  az acr login -n $AcrName

  docker build -t "$loginServer/target-manager:$ImageTag" -f target-manager/Dockerfile target-manager
  docker push "$loginServer/target-manager:$ImageTag"
}

Write-Host "== Install ingress-nginx (requires Helm) =="
$helm = Get-Command helm -ErrorAction SilentlyContinue
if (-not $helm) {
  Write-Host "Helm not found. Install Helm then re-run this section:" -ForegroundColor Yellow
  Write-Host "  choco install kubernetes-helm" -ForegroundColor Yellow
} else {
  helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
  helm repo update
  helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx --namespace ingress-nginx --create-namespace
}

Write-Host "== Apply manifests =="
# 1) Create secrets: edit k8s/secret.example.yaml and apply it.
#    Or create via kubectl create secret generic ...
# 2) Ensure k8s/ingress.yaml host matches your DNS (or temporarily use the LB IP directly).

kubectl apply -n $Namespace -f k8s/service.yaml
kubectl apply -n $Namespace -f k8s/deployment.yaml
kubectl apply -n $Namespace -f k8s/network-policies.yaml
kubectl apply -n $Namespace -f k8s/ingress.yaml

Write-Host "== Next checks =="
Write-Host "kubectl get pods -n $Namespace"
Write-Host "kubectl logs deployment/target-manager -n $Namespace"
Write-Host "kubectl get ingress -n $Namespace"
Write-Host "kubectl get svc -n ingress-nginx"
