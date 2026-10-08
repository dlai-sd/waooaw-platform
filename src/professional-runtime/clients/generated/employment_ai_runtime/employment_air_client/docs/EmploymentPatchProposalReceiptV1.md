# EmploymentPatchProposalReceiptV1


## Properties

Name | Type | Description | Notes
------------ | ------------- | ------------- | -------------
**schema_version** | [**AirEmploymentSchemaVersion**](AirEmploymentSchemaVersion.md) |  | 
**proposal_id** | **str** |  | 
**state** | **str** |  | 
**protocol_version** | **str** |  | 
**relationship_ref** | **str** |  | 
**contribution_ref** | **str** |  | 
**agent_type** | **str** |  | 
**agent_version** | **str** |  | 
**manifest_version** | **str** |  | 
**patch_type** | [**ProposalPatchType**](ProposalPatchType.md) |  | 
**semantic_catalogue** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**prompt_policy** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**model_policy** | [**ImmutableContractReferenceV1**](ImmutableContractReferenceV1.md) |  | 
**request_digest** | **str** |  | 
**accepted_at** | **datetime** |  | 
**reconciliation_uri** | **str** |  | 

## Example

```python
from employment_air_client.models.employment_patch_proposal_receipt_v1 import EmploymentPatchProposalReceiptV1

# TODO update the JSON string below
json = "{}"
# create an instance of EmploymentPatchProposalReceiptV1 from a JSON string
employment_patch_proposal_receipt_v1_instance = EmploymentPatchProposalReceiptV1.from_json(json)
# print the JSON string representation of the object
print(EmploymentPatchProposalReceiptV1.to_json())

# convert the object into a dict
employment_patch_proposal_receipt_v1_dict = employment_patch_proposal_receipt_v1_instance.to_dict()
# create an instance of EmploymentPatchProposalReceiptV1 from a dict
employment_patch_proposal_receipt_v1_from_dict = EmploymentPatchProposalReceiptV1.from_dict(employment_patch_proposal_receipt_v1_dict)
```
[[Back to Model list]](../README.md#documentation-for-models) [[Back to API list]](../README.md#documentation-for-api-endpoints) [[Back to README]](../README.md)


