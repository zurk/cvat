from copy import deepcopy
import json

labels_template = {
    "name": "1",
    "attributes": [
        {
            "name": "direction",
            "mutable": False,
            "input_type": "radio",
            "default_value": "",
            "values": ["", "in", "out"],
        },
    ],
}

labels = []
for i in range(1, 25):
    cur_labels = deepcopy(labels_template)
    cur_labels["name"] = str(i)
    labels.append(cur_labels)

with open("labels-tram.json", "w") as f:
    json.dump(labels, f, indent=2)
