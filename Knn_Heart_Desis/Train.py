import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.metrics import accuracy_score, confusion_matrix, classification_report
import joblib

# 1. Load dataset
data = pd.read_csv("heart_disease_dataset_1000.csv")

# 2. Split features and target
X = data.drop("target", axis=1)
y = data["target"]

# 3. Train Test Split
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42
)

# 4. Create KNN Model
knn = KNeighborsClassifier(n_neighbors=5)

# 5. Train Model
knn.fit(X_train, y_train)

# 6. Predictions
y_pred = knn.predict(X_test)

# 7. Accuracy
accuracy = accuracy_score(y_test, y_pred)
print("Model Accuracy:", accuracy * 100, "%")

# 8. Confusion Matrix
print("\nConfusion Matrix")
print(confusion_matrix(y_test, y_pred))

# 9. Classification Report
print("\nClassification Report")
print(classification_report(y_test, y_pred))

# 10. Save Model
joblib.dump(knn, "heart_knn_model.pkl")

print("\nModel saved as heart_knn_model.pkl")