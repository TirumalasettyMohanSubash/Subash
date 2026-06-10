import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
import matplotlib.pyplot as plt
import joblib

def train_model():
    print("Loading dataset...")
    data = pd.read_csv('data.csv')

    X = data[['Area','Bedrooms']]  ## input
    y = data['Price']               ## output
    X_train,X_test,y_train,y_test = train_test_split(X,y,test_size=0.2,random_state=42)

    print("Traininng model...")
    model = LinearRegression()
    model.fit(X_train,y_train)

    pred = model.predict(X_test)
    accuracy = round(r2_score(y_test,pred)*100,2)
    joblib.dump(model,"model.pkl")

    plt.figure()
    plt.bar(["Accuracy"],[accuracy])
    plt.title("Model Accuracy")
    plt.savefig("static/accuracy.png")
    plt.close()

    print("Accuracy:",accuracy)

    return accuracy

if __name__ == "__main__":
    print(train_model())
