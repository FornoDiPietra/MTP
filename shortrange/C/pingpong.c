#include <wiringPi.h>
#include <wiringPiSPI.h>

#include <stdio.h>
#include <stdlib.h>
#include <time.h>

void transmit(char *data) {

	//1010 0000 -> 0xA0 W_TX_PAYLOAD
	char W_TX_PAYLOAD = 0xA0;
	char buf[33];
	int ret;

	buf[0] = W_TX_PAYLOAD;
	for (int i=1;i<33; i++) {
		buf[i] = data[i]; 
	}

	wiringPiSPIDataRW(0, buf, 33);
	printf("W_TX: %d\n",buf[0]);
}

void read_reg() {
	//000A AAAA
	char R_READ = 0x00 | 0x00;
	char buf[2];

	buf[0] = R_READ;
	buf[1] = 0x00;

	wiringPiSPIDataRW (0, buf, 2) ;
	printf("%d, %d\n", buf[0], buf[1]);
}

void clearIRQ() {
	//001A AAAA
	char addr = 7;
	char R_WRITE = 0x20 | addr;
	char buf[2];

	buf[0] = R_WRITE;
	buf[1] = 0xff;

	wiringPiSPIDataRW (0, buf, 2) ;
}

int main (void)
{
	//int wiringPiSPISetup (int channel, int speed) ;
	int val = wiringPiSPISetup(0, 500000);
	printf("spi init: %d\n",val);

	//int wiringPiSPIDataRW (int channel, unsigned char *data, int len) ;

	//wiringPiSPIDataRW (0, unsigned char *data, int len) ;
	char data[32];
	for (int i;i<32;i++) {
		data[i] = 0x00;
	}

  	wiringPiSetup () ;

  	read_reg();

  	#define IRQ_TX 6

	pinMode (16, INPUT);
	pinMode (IRQ_TX, INPUT);
	int readPin = digitalRead(IRQ_TX);

	clearIRQ();
	printf("IRQ_TX: %d\n", readPin);

	transmit(data);
	readPin = digitalRead(IRQ_TX);
	printf("IRQ_TX: %d\n", readPin);

	clearIRQ();
	readPin = digitalRead(IRQ_TX);
	printf("IRQ_TX: %d\n", readPin);

  return 0 ;
}