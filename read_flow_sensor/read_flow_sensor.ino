// Read & print integer value from flow sensor


#define flowSensor_pin A0

int flowSensor_reading;


void setup() {
  Serial.begin(9600);
  pinMode(flowSensor_pin, INPUT);
}


void loop() {
  
  flowSensor_reading = analogRead(flowSensor_pin);
  Serial.println(flowSensor_reading);
  
  delay(50);

}
