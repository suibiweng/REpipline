import json
import torch
import numpy as np
import torch.nn as nn
import argparse
from transformers import BertTokenizer, BertModel
import spacy

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# -------------------------------
# 1. Text Encoder (Using BERT)
# -------------------------------
class TextEncoder(nn.Module):
    def __init__(self, model_name="bert-base-uncased", embedding_dim=256):
        super().__init__()
        self.tokenizer = BertTokenizer.from_pretrained(model_name)
        self.bert = BertModel.from_pretrained(model_name)
        self.fc = nn.Linear(self.bert.config.hidden_size, embedding_dim)

    def forward(self, text_list):
        tokens = self.tokenizer(text_list, return_tensors="pt", padding=True, truncation=True)
        tokens = {k: v.to(device) for k, v in tokens.items()}
        outputs = self.bert(**tokens)
        cls_emb = outputs.last_hidden_state[:, 0, :]
        return self.fc(cls_emb)

# -------------------------------
# 2. Coordinate Generator per Object
# -------------------------------
class CoordinateGenerator(nn.Module):
    def __init__(self, input_dim=256):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.1),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, 5)
        )

    def forward(self, features):
        return self.mlp(features)

# ---------------------------------------
# 3. Full Pipeline (without relations)
# ---------------------------------------
class TextTo3DModel(nn.Module):
    def __init__(self, embedding_dim=256):
        super().__init__()
        self.text_encoder = TextEncoder(embedding_dim=embedding_dim)
        self.generator = CoordinateGenerator(input_dim=embedding_dim)

    def forward(self, object_sentences):
        text_emb = self.text_encoder(object_sentences)  # (N, D)
        return self.generator(text_emb)                 # (N, 5)

def get_scene_objects(doc):
    objs = []
    for chunk in doc.noun_chunks:
        if any(child.dep_ == "prep" for child in chunk.root.children):
            continue
        objs.append(chunk.text)
    return objs

def infer_example(model_path, sentence, output_path=None):
    ckpt = torch.load(model_path, map_location=device)
    loc_means = np.array(ckpt['loc_means'], dtype=float)
    loc_stds = np.array(ckpt['loc_stds'], dtype=float)

    model = TextTo3DModel(embedding_dim=256).to(device)
    model.load_state_dict(ckpt['state'])
    model.eval()

    nlp = spacy.load("en_core_web_sm")
    doc = nlp(sentence)
    object_names = get_scene_objects(doc)
    object_sentences = [f"{sentence} [OBJ] {obj}" for obj in object_names]

    with torch.no_grad():
        preds = model(object_sentences).cpu().numpy()

    output = []
    for obj_name, pred in zip(object_names, preds):
        loc_norm = pred[:3]
        loc = (loc_norm * loc_stds + loc_means).tolist()
        rot = float(pred[3] * 100)
        size = float(pred[4])

        obj = {
            "name": obj_name,
            "transform": {
                "position": {
                    "x": round(loc[0], 2),
                    "y": round(loc[2], 2),
                    "z": round(loc[1], 2)
                },
                "rotation": {
                    "x": round(rot, 2),
                    "y": round(rot, 2),
                    "z": round(rot, 2)
                },
                "size": {
                    "x": round(size, 2),
                    "y": round(size, 2),
                    "z": round(size, 2)
                }
            },
            "url": "",
            "id": ""
        }
        output.append(obj)

    # Print to console
    print(json.dumps(output, indent=2))

    # Save to file if output_path is provided
    if output_path:
        with open(output_path, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"Saved results to {output_path}")

    return output

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Text-to-3D inference")
    parser.add_argument('--model_path', type=str, required=True, help="Path to the trained model (.pth)")
    parser.add_argument('--sentence', type=str, required=True, help="Input sentence to infer 3D coordinates")
    parser.add_argument('--output_path', type=str, required=False, help="Optional path to save output JSON file")
    
    args = parser.parse_args()
    
    infer_example(args.model_path, args.sentence, args.output_path)
