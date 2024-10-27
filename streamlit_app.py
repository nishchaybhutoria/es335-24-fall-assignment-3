import torch
import streamlit as st
from torch import nn
import torch.nn.functional as F
import json
import re

class NextWord(nn.Module):
    def __init__(self, block_size, vocab_size, embedding_dim, hidden_dim, activation_fn):
        super(NextWord, self).__init__()
        self.embedding = nn.Embedding(vocab_size, embedding_dim)
        self.lin1 = nn.Linear(embedding_dim * block_size, hidden_dim)
        self.lin2 = nn.Linear(hidden_dim, hidden_dim)
        self.lin3 = nn.Linear(hidden_dim, hidden_dim)
        self.lin4 = nn.Linear(hidden_dim, hidden_dim)
        self.activation = activation_fn
        self.lin_out = nn.Linear(hidden_dim, vocab_size)

    def forward(self, x):
        embeds = self.embedding(x)  # Shape: (batch_size, block_size, embedding_dim)
        embeds = embeds.view(x.shape[0], -1)  # Flatten: (batch_size, block_size * embedding_dim)
        out = self.activation(self.lin1(embeds))
        out = self.activation(self.lin2(out))
        out = self.activation(self.lin3(out))
        out = self.activation(self.lin4(out))
        return self.lin_out(out)  # Shape: (batch_size, vocab_size)

def load_model(model_path, block_size, vocab_size, embedding_dim, hidden_dim, activation_fn):
    print(model_path)
    model = NextWord(block_size, vocab_size, embedding_dim, hidden_dim, activation_fn)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()    
    return model

def load_vocab(corpus):
    stoi_path=f'stoi_{corpus}.json'
    itos_path=f'itos_{corpus}.json'
    with open(stoi_path, 'r') as f:
        stoi = json.load(f)
    with open(itos_path, 'r') as f:
        itos = json.load(f)
    return stoi, itos

def generate_sequence_sherlock(model, itos, stoi, context_words, block_size, max_len=20):
    unk_idx = stoi.get('<UNK>', 0)  # Get index for unknown words, default to 0 if <UNK> not found
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # Define device

    # Move model to the same device
    model = model.to(device)

    # Convert context words to indices, map unknown words to <UNK>
    context = [stoi.get(word, unk_idx) for word in context_words]

    # Pad context if it's shorter than block_size
    if len(context) < block_size:
        pad_idx = stoi.get('<UNK>', unk_idx)  # Use <UNK> for padding if available
        context = [pad_idx] * (block_size - len(context)) + context

    sequence = context_words.copy()
    capitalize_next = False  # Flag to determine if the next word should be capitalized

    # If the last word in context ends with a period, set the flag
    if sequence and sequence[-1].endswith('.'):
        capitalize_next = True

    with torch.no_grad():
        for _ in range(max_len):
            # Prepare input tensor and move it to the correct device
            x = torch.tensor(context[-block_size:], dtype=torch.long).unsqueeze(0).to(device)  # Shape: [1, block_size]

            # Get model predictions
            y_pred = model(x)  # [1, vocab_size]

            # Apply softmax to get probabilities
            probs = F.softmax(y_pred, dim=1)

            # Sample from the distribution
            ix = torch.multinomial(probs, num_samples=1).item()
            word = itos.get(str(ix), '<UNK>')

            # Determine if the word is punctuation
            is_punct = word in {'.', ',', '!', '?'}

            # Capitalize the word if the flag is set and it's not punctuation
            if capitalize_next and not is_punct and word != '<PAR_BREAK>':
                word = word.capitalize()
                capitalize_next = False  # Reset the flag after capitalizing

            # Handle paragraph breaks
            if word == '<PAR_BREAK>':
                sequence.append('\n')  # Add a newline to represent the paragraph break
                capitalize_next = True  # Capitalize the first word after a paragraph break
            else:
                # Append the generated word to the sequence
                sequence.append(word)

            # Update the context with the generated word's index
            context.append(ix)

            # If the generated word is a period, set the flag to capitalize the next word
            if word.endswith('.'):
                capitalize_next = True

    # Post-processing to remove spaces before punctuation marks
    generated_text = ' '.join(sequence)

    # Remove space before punctuation marks
    generated_text = re.sub(r'\s+([.,!?])', r'\1', generated_text)
    print(generated_text)
    return generated_text


def generate_sequence_lyrics(model, itos, stoi, context_words, block_size, max_len=20):
    unk_idx = stoi.get('<UNK>', 0)  # Get index for unknown words, default to 0 if <UNK> not found
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # Define device

    # Move model to the same device
    model = model.to(device)
    
    # Convert context words to indices, map unknown words to <UNK>
    context = [stoi.get(word, unk_idx) for word in context_words]
    
    # Pad context if it's shorter than block_size
    if len(context) < block_size:
        pad_idx = stoi.get('<UNK>', unk_idx)  # Use <UNK> for padding if available
        context = [pad_idx] * (block_size - len(context)) + context
    
    sequence = context_words.copy()
    capitalize_next = False  # Flag to determine if the next word should be capitalized
    
    # If the last word in context ends with a period, set the flag
    if sequence and sequence[-1].endswith('.'):
        capitalize_next = True
    
    with torch.no_grad():
        for _ in range(max_len):
            # Prepare input tensor
            x = torch.tensor(context[-block_size:], dtype=torch.long).unsqueeze(0).to(device)  # Shape: [1, block_size]
            
            # Get model predictions
            y_pred = model(x)  # [1, vocab_size]
            
            # Apply softmax to get probabilities
            probs = F.softmax(y_pred, dim=1)
            
            # Sample from the distribution
            ix = torch.multinomial(probs, num_samples=1).item()
            word = itos.get(str(ix), '<UNK>')  # Convert ix to a string

            
            # Determine if the word is punctuation
            is_punct = word in {'.', ',', '!', '?'}
            
            # Capitalize the word if the flag is set and it's not punctuation
            if capitalize_next and not is_punct and word != '<PAR_BREAK>':
                word = word.capitalize()
                capitalize_next = False  # Reset the flag after capitalizing
            
            # Handle paragraph breaks
            if word == '<PAR_BREAK>':
                sequence.append('\n')  # Add a newline to represent the paragraph break
                capitalize_next = True  # Capitalize the first word after a paragraph break
            else:
                # Append the generated word to the sequence
                sequence.append(word)
            
            # Update the context with the generated word's index
            context.append(ix)
            
            # If the generated word is a period, set the flag to capitalize the next word
            if word.endswith('.'):
                capitalize_next = True
    
    # Post-processing to remove spaces before punctuation marks
    generated_text = ' '.join(sequence)
    # Remove space before punctuation marks
    generated_text = re.sub(r'\s+([.,!?])', r'\1', generated_text)
    # Remove spaces around apostrophes
    generated_text = re.sub(r"\s*'\s*", "'", generated_text)
    print(generated_text)
    return generated_text

def generate_sequence_c(model, itos, stoi, context_words, block_size, max_len=20):
    """
    Generates a sequence of C code tokens based on the provided context.
    Treats punctuation, newline, and space tokens appropriately for code formatting.
    Ensures that punctuation and special tokens are appended correctly without additional spaces.
    """
    unk_idx = stoi.get('<UNK>', 0)  # Index for unknown words
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")  # Define device
    model = model.to(device)
    # Convert context words to indices, mapping unknown words to <UNK>
    context = [stoi.get(word, unk_idx) for word in context_words]
    
    # Pad context if it's shorter than block_size
    if len(context) < block_size:
        context = [unk_idx] * (block_size - len(context)) + context
    
    sequence = context_words.copy()
    generated_code = ''  # Initialize an empty string to build generated code
    
    with torch.no_grad():
        for _ in range(max_len):
            # Prepare input tensor
            x = torch.tensor(context[-block_size:]).unsqueeze(0).to(device)  # Shape: [1, block_size]
            
            # Get model predictions
            y_pred = model(x)  # [1, vocab_size]
            
            # Apply softmax to get probabilities
            probs = F.softmax(y_pred, dim=1)
            
            # Sample from the distribution
            ix = torch.multinomial(probs, num_samples=1).item()
            word = itos.get(str(ix), '<UNK>')
            
            # Convert \n and \s escape sequences to actual characters
            if word == '\n':
                generated_code += '\n'
            elif word == '\s':
                generated_code += ' '
            else:
                generated_code += word  # Append token without spaces
            
            # Update the context with the generated word's index
            context.append(ix)
    
    return generated_code

def generate_sequence_wiki():
    return

def main():
    st.title("Next Word Prediction - Text Corpus")

    # Corpus and Model Hyperparameters Selection
    corpus = st.selectbox("Select Corpus", ["sherlock", "c", "lyrics", "wiki"])
    block_size = st.selectbox("Select Block Size", [5, 10, 15])
    embedding_dim = st.selectbox("Select Embedding Dimension", [64, 128])
    activation_fn_name = st.selectbox("Select Activation Function", ["ReLU", "Tanh"])
    activation_fn = nn.Tanh() if activation_fn_name == "Tanh" else nn.ReLU()

    # Initialize session state for storing the model and vocab
    if 'model' not in st.session_state:
        st.session_state.model = None
    if 'stoi' not in st.session_state:
        st.session_state.stoi = None
    if 'itos' not in st.session_state:
        st.session_state.itos = None

    # Dynamically generate the model path
    model_path = f'models/{corpus}_nextword_model_bs{block_size}_emb{embedding_dim}_act{activation_fn_name}.pth'

    # Load Model Button
    if st.button("Load Model"):
        st.write(f"Loading model from: {model_path}")

        # Load the vocab and model
        stoi, itos = load_vocab(corpus)
        hidden_dim = 256

        # Load the model and store it in session state
        st.session_state.model = load_model(model_path, block_size, len(stoi) + 1, embedding_dim, hidden_dim, activation_fn)
        st.session_state.stoi = stoi
        st.session_state.itos = itos
        st.write("Model loaded successfully!")

    # Only display input fields and generate button if the model is loaded
    if st.session_state.model:
        # Input Text and Word Generation Length
        input_text = st.text_input("Enter the text:", "")
        k = st.number_input("How many words to generate?", min_value=1, max_value=100, value=5)

        # 'Generate' Button
        if st.button("Generate"):
            if input_text:  # Ensure input text is provided
                context_words = input_text.split()

                # Call the appropriate sequence generation function based on the selected corpus
                if corpus == 'sherlock':
                    generated_text = generate_sequence_sherlock(st.session_state.model, st.session_state.itos, st.session_state.stoi, context_words, block_size, max_len=k)
                elif corpus == 'lyrics':
                    generated_text = generate_sequence_lyrics(st.session_state.model, st.session_state.itos, st.session_state.stoi, context_words, block_size, max_len=k)
                elif corpus == 'c':
                    generated_text = generate_sequence_c(st.session_state.model, st.session_state.itos, st.session_state.stoi, context_words, block_size, max_len=k)
                elif corpus == 'wiki':
                    generated_text = generate_sequence_wiki(st.session_state.model, st.session_state.itos, st.session_state.stoi, context_words, block_size, max_len=k)

                st.write(f"Generated words: {generated_text}")
            else:
                st.write("Please enter some text to generate from.")
    else:
        st.write("Please load the model first to generate words.")

# Run the app
if __name__ == "__main__":
    main()