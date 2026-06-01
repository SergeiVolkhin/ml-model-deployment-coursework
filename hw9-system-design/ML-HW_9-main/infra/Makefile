# Удобные команды для работы со стендом.
# Все цели идемпотентны: повторный apply не пересоздаёт ресурсы.

TF      ?= terraform
TF_DIR  ?= infra

.PHONY: init plan apply destroy fmt validate lint help

help:
	@echo "Цели: init plan apply destroy fmt validate lint"

init:
	$(TF) -chdir=$(TF_DIR) init

plan:
	$(TF) -chdir=$(TF_DIR) plan -out=tfplan

apply:
	$(TF) -chdir=$(TF_DIR) apply -auto-approve tfplan

destroy:
	$(TF) -chdir=$(TF_DIR) destroy -auto-approve

fmt:
	$(TF) -chdir=$(TF_DIR) fmt -recursive

validate:
	$(TF) -chdir=$(TF_DIR) fmt -check -recursive
	$(TF) -chdir=$(TF_DIR) validate

lint:
	tflint --chdir=$(TF_DIR)
