import pandas as pd
import pickle

from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler, LabelEncoder
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense

# 🔹 Load dataset
data = pd.read_csv("dataset_10.csv")

# 🔹 Remove unwanted columns (if any like 'Unnamed: 0')
data = data.loc[:, ~data.columns.str.contains('^Unnamed')]

# 🔹 Features & Target
X = data.drop("disease", axis=1)   # 10 input features
y = data["disease"]

# 🔹 Debug check (IMPORTANT)
print("Features used:", X.columns.tolist())
print("Shape of X:", X.shape)   # Should be (rows, 10)

# 🔹 Encode target labels
label_encoder = LabelEncoder()
y_encoded = label_encoder.fit_transform(y)

# Save label encoder
with open("label_encoder.pkl", "wb") as f:
    pickle.dump(label_encoder, f)

# 🔹 Scale features
scaler = StandardScaler()
X_scaled = scaler.fit_transform(X)

# Save scaler
with open("scaler.pkl", "wb") as f:
    pickle.dump(scaler, f)

# 🔹 Train-test split
X_train, X_test, y_train, y_test = train_test_split(
    X_scaled, y_encoded, test_size=0.2, random_state=42
)

# 🔹 Build ANN model
model = Sequential()
model.add(Dense(16, activation='relu', input_dim=X_train.shape[1]))
model.add(Dense(12, activation='relu'))
model.add(Dense(len(set(y_encoded)), activation='softmax'))

# 🔹 Compile model
model.compile(
    optimizer='adam',
    loss='sparse_categorical_crossentropy',
    metrics=['accuracy']
)

# 🔹 Train model
model.fit(X_train, y_train, epochs=30, batch_size=8)

# 🔹 Evaluate (optional but good practice)
loss, acc = model.evaluate(X_test, y_test)
print(f"Model Accuracy: {acc*100:.2f}%")

# 🔹 Save model
model.save("disease_model.h5")

print("✅ Model trained and saved successfully!")