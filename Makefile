# Azure infrastructure deployment for Odin
# Resource group: Valhalla
# Usage: make check | make rg | make validate ENV=dev | make whatif ENV=dev | make deploy ENV=dev | make outputs ENV=dev

RG_NAME := Valhalla
RG_LOCATION := canadaeast
TEMPLATE := infra/main.bicep
ENV ?= dev
PARAMS := infra/params/$(ENV).json
TIMESTAMP := $(shell date +%Y%m%d%H%M%S)
DEPLOYMENT_NAME := odin-$(ENV)-$(TIMESTAMP)

# Optional: set AZ_SUBSCRIPTION to target a specific subscription
ifdef AZ_SUBSCRIPTION
AZ_SET_SUBSCRIPTION := az account set --subscription "$(AZ_SUBSCRIPTION)" &&
endif

.PHONY: check providers rg validate whatif deploy outputs help

help:
	@echo "Azure infra deployment targets:"
	@echo "  make check          - Verify az CLI and show active account"
	@echo "  make providers      - Register required Azure resource providers"
	@echo "  make rg             - Ensure resource group Valhalla exists"
	@echo "  make validate ENV=  - Validate Bicep template (default ENV=dev)"
	@echo "  make whatif ENV=    - Preview deployment changes (default ENV=dev)"
	@echo "  make deploy ENV=    - Deploy infrastructure (default ENV=dev)"
	@echo "  make outputs ENV=   - Print last deployment outputs (default ENV=dev)"
	@echo ""
	@echo "Examples: make deploy ENV=prod  |  AZ_SUBSCRIPTION=my-sub make deploy"

check:
	@command -v az >/dev/null 2>&1 || (echo "Error: Azure CLI (az) not found. Install: https://docs.microsoft.com/en-us/cli/azure/install-azure-cli" && exit 1)
	@echo "Azure CLI found. Active account:"
	@az account show -o table

providers:
	@echo "Registering resource providers..."
	@az provider register --namespace Microsoft.App --wait
	@az provider register --namespace Microsoft.OperationalInsights --wait
	@az provider register --namespace Microsoft.Insights --wait
	@az provider register --namespace Microsoft.KeyVault --wait
	@az provider register --namespace Microsoft.Storage --wait
	@echo "Providers registered."

rg:
	@echo "Ensuring resource group $(RG_NAME) in $(RG_LOCATION)..."
	@$(AZ_SET_SUBSCRIPTION) az group create --name $(RG_NAME) --location $(RG_LOCATION) -o table

validate: check rg
	@test -f $(PARAMS) || (echo "Error: params file not found: $(PARAMS)" && exit 1)
	@echo "Validating $(TEMPLATE) with $(PARAMS)..."
	@$(AZ_SET_SUBSCRIPTION) az deployment group validate \
		--resource-group $(RG_NAME) \
		--template-file $(TEMPLATE) \
		--parameters @$(PARAMS) \
		--output table

whatif: check rg
	@test -f $(PARAMS) || (echo "Error: params file not found: $(PARAMS)" && exit 1)
	@echo "Previewing deployment to $(RG_NAME) with $(PARAMS)..."
	@$(AZ_SET_SUBSCRIPTION) az deployment group what-if \
		--resource-group $(RG_NAME) \
		--template-file $(TEMPLATE) \
		--parameters @$(PARAMS) \
		--name $(DEPLOYMENT_NAME)

deploy: check rg
	@test -f $(PARAMS) || (echo "Error: params file not found: $(PARAMS)" && exit 1)
	@echo "Deploying to $(RG_NAME) with $(PARAMS)..."
	@$(AZ_SET_SUBSCRIPTION) az deployment group create \
		--resource-group $(RG_NAME) \
		--template-file $(TEMPLATE) \
		--parameters @$(PARAMS) \
		--name $(DEPLOYMENT_NAME) \
		--output table

outputs: check
	@echo "Last deployment outputs for $(RG_NAME):"
	@$(AZ_SET_SUBSCRIPTION) az deployment group show \
		--resource-group $(RG_NAME) \
		--name $$(az deployment group list --resource-group $(RG_NAME) --query "[0].name" -o tsv) \
		--query properties.outputs -o json 2>/dev/null || echo "No deployment found. Run 'make deploy ENV=$(ENV)' first."
