// Copyright (c) 2021 David G. Young
// Copyright (c) 2015 Damian Kołakowski. All rights reserved.

// cc bt_beacon_accelerometer_scanner.c -lbluetooth -o bt_beacon_accelerometer_scanner

#include <stdio.h>
#include <stdint.h>
#include <time.h>
#include <unistd.h>
#include <string.h>
#include <stdlib.h>
#include <signal.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <errno.h>
#include <sys/ioctl.h>
#include <bluetooth/bluetooth.h>
#include <bluetooth/hci.h>
#include <bluetooth/hci_lib.h>


int device;
const char target_mac[] = "ZZZZ"; // Replace with your target MAC address

struct hci_request ble_hci_request(uint16_t ocf, int clen, void * status, void * cparam)
{
	struct hci_request rq;
	memset(&rq, 0, sizeof(rq));
	rq.ogf = OGF_LE_CTL;
	rq.ocf = ocf;
	rq.cparam = cparam;
	rq.clen = clen;
	rq.rparam = status;
	rq.rlen = 1;
	return rq;
}

// cleanup and exit the program with exit code 0
void exit_clean()
{
	int ret, status;

	// Disable scanning.

	le_set_scan_enable_cp scan_cp;
	memset(&scan_cp, 0, sizeof(scan_cp));
	scan_cp.enable = 0x00;	// Disable flag.

	struct hci_request disable_adv_rq = ble_hci_request(OCF_LE_SET_SCAN_ENABLE, LE_SET_SCAN_ENABLE_CP_SIZE, &status, &scan_cp);
	ret = hci_send_req(device, &disable_adv_rq, 1000);
	if ( ret < 0 )
		perror("Failed to disable scan.");

	hci_close_dev(device);
	exit( 0 );
}

// handles timeout
void signal_handler( int s )
{
	//printf( "received SIGALRM\n" );
	exit_clean();
}

void write_to_csv(const char *filename, int16_t battery, int16_t x, int16_t y, int16_t z) {
    FILE *file = fopen(filename, "a");
    if (file == NULL) {
        perror("Unable to open file");
        return;
    }

    // Check if the file is empty to write headers
    fseek(file, 0, SEEK_END);
    if (ftell(file) == 0) {
        fprintf(file, "Datetime,Battery (mV),X,Y,Z\n");
    }

    // Get current time
    struct timespec ts;
    timespec_get(&ts, TIME_UTC);
    struct tm *tm_info = localtime(&ts.tv_sec);

    // Format time to include milliseconds
    char time_buffer[30];
    strftime(time_buffer, sizeof(time_buffer), "%m/%d/%Y %H:%M:%S", tm_info);
    snprintf(time_buffer + strlen(time_buffer), sizeof(time_buffer) - strlen(time_buffer), ":%03ld", ts.tv_nsec / 1000000);

    // Write to CSV
    fprintf(file, "%s,%d,%d,%d,%d\n", time_buffer, battery, x, y, z);
    fclose(file);
}

void process_data(const le_advertising_info *info) {
    if (info->length >= 10) {
    	int8_t battery_byte_1 = (int8_t)info->data[info->length-10];
    	int8_t battery_byte_2 = (int8_t)info->data[info->length-9];
        int8_t accelerometer_x_byte1 = (int8_t)info->data[info->length - 6];
        int8_t accelerometer_x_byte2 = (int8_t)info->data[info->length - 5];
        int8_t accelerometer_y_byte1 = (int8_t)info->data[info->length - 4];
        int8_t accelerometer_y_byte2 = (int8_t)info->data[info->length - 3];
        int8_t accelerometer_z_byte1 = (int8_t)info->data[info->length - 2];
        int8_t accelerometer_z_byte2 = (int8_t)info->data[info->length - 1];

        int16_t x = (int16_t)((accelerometer_x_byte1 << 8) | (uint8_t)accelerometer_x_byte2);
        int16_t y = (int16_t)((accelerometer_y_byte1 << 8) | (uint8_t)accelerometer_y_byte2);
        int16_t z = (int16_t)((accelerometer_z_byte1 << 8) | (uint8_t)accelerometer_z_byte2);
        int16_t battery = (int16_t)((battery_byte_1 << 8) | (uint8_t)battery_byte_2);

        write_to_csv("/home/flashsysXXX/data/123XXX_data/123XXX_beacon_data_output.csv", battery, x, y, z);
    }
}



int main()
{
	int ret, status;

	// Get HCI device.

	device = hci_open_dev(1);
	if ( device < 0 ) {
		device = hci_open_dev(0);
		if (device >= 0) {
   		printf("Using hci0\n");
		}
	}
	else {
   		printf("Using hci1\n");
	}

	if ( device < 0 ) {
		perror("Failed to open HCI device.");
		return 0;
	}

	// Set BLE scan parameters.

	le_set_scan_parameters_cp scan_params_cp;
	memset(&scan_params_cp, 0, sizeof(scan_params_cp));
	scan_params_cp.type 			= 0x00;
	scan_params_cp.interval 		= htobs(0x0010);
	scan_params_cp.window 			= htobs(0x0010);
	scan_params_cp.own_bdaddr_type 	= 0x00; // Public Device Address (default).
	scan_params_cp.filter 			= 0x00; // Accept all.

	struct hci_request scan_params_rq = ble_hci_request(OCF_LE_SET_SCAN_PARAMETERS, LE_SET_SCAN_PARAMETERS_CP_SIZE, &status, &scan_params_cp);

	ret = hci_send_req(device, &scan_params_rq, 1000);
	if ( ret < 0 ) {
		hci_close_dev(device);
		perror("Failed to set scan parameters data.");
		return 0;
	}

	// Set BLE events report mask.

	le_set_event_mask_cp event_mask_cp;
	memset(&event_mask_cp, 0, sizeof(le_set_event_mask_cp));
	int i = 0;
	for ( i = 0 ; i < 8 ; i++ ) event_mask_cp.mask[i] = 0xFF;

	struct hci_request set_mask_rq = ble_hci_request(OCF_LE_SET_EVENT_MASK, LE_SET_EVENT_MASK_CP_SIZE, &status, &event_mask_cp);
	ret = hci_send_req(device, &set_mask_rq, 1000);
	if ( ret < 0 ) {
		hci_close_dev(device);
		perror("Failed to set event mask.");
		return 0;
	}

	// Enable scanning.

	le_set_scan_enable_cp scan_cp;
	memset(&scan_cp, 0, sizeof(scan_cp));
	scan_cp.enable 		= 0x01;	// Enable flag.
	scan_cp.filter_dup 	= 0x00; // Filtering disabled.

	struct hci_request enable_adv_rq = ble_hci_request(OCF_LE_SET_SCAN_ENABLE, LE_SET_SCAN_ENABLE_CP_SIZE, &status, &scan_cp);

	ret = hci_send_req(device, &enable_adv_rq, 1000);
	if ( ret < 0 ) {
		hci_close_dev(device);
		perror("Failed to enable scan.");
		return 0;
	}

	// Get Results.

	struct hci_filter nf;
	hci_filter_clear(&nf);
	hci_filter_set_ptype(HCI_EVENT_PKT, &nf);
	hci_filter_set_event(EVT_LE_META_EVENT, &nf);
	if ( setsockopt(device, SOL_HCI, HCI_FILTER, &nf, sizeof(nf)) < 0 ) {
		hci_close_dev(device);
		perror("Could not set socket options\n");
		return 0;
	}


	uint8_t buf[HCI_MAX_EVENT_SIZE];
	evt_le_meta_event * meta_event;
	le_advertising_info * info;
	int len;
	int count = 0;

	const int timeout = 40;
	const int reset_timeout = 1; // wether to reset the timer on a received scan event (continuous scanning)
	// const int max_count = 10000;

	// Install a signal handler so that we can set the exit code and clean up
	if ( signal( SIGALRM, signal_handler ) == SIG_ERR )
	{
		hci_close_dev(device);
		perror( "Could not install signal handler\n" );
		return 0;
	}

	if ( timeout > 0 )
		alarm( timeout ); // set the alarm timer, when time is up the program will be terminated

	sigset_t sigalrm_set; // apparently the signal must be unblocked in some cases
	sigemptyset ( &sigalrm_set );
	sigaddset ( &sigalrm_set, SIGALRM );
	if ( sigprocmask( SIG_UNBLOCK, &sigalrm_set, NULL ) != 0 )
	{
		hci_close_dev(device);
		perror( "Could not unblock alarm signal" );
		return 0;
	}

	// Keep scanning until the timeout is triggered or we have seen lots of advertisements.  Then exit.
	// We exit in this case because the scan may have failed or stopped. Higher level code can restart
	while (1) // while (count < max_count || max_count <= 0)
	{
		len = read(device, buf, sizeof(buf));
		if ( len >= HCI_EVENT_HDR_SIZE )
		{
			meta_event = (evt_le_meta_event*)(buf+HCI_EVENT_HDR_SIZE+1);
			if ( meta_event->subevent == EVT_LE_ADVERTISING_REPORT )
			{
				count++;
				if ( reset_timeout != 0 && timeout > 0 ) // reset/restart the alarm timer
					alarm( timeout );

				// print results
				uint8_t reports_count = meta_event->data[0];
				void * offset = meta_event->data + 1;
				while (reports_count--) {
				    info = (le_advertising_info *)offset;
				    char addr[18];
				    ba2str(&(info->bdaddr), addr);
				    if (strcmp(addr, target_mac) == 0) { // Check if the MAC address matches the target
					// Check if the advertising data starts with the specified pattern
					if (info->length >= 12 && 
					    info->data[0] == 0x02 && info->data[1] == 0x01 && info->data[2] == 0x06 &&
					    info->data[3] == 0x03 && info->data[4] == 0x03 && info->data[5] == 0xAA && info->data[6] == 0xFE &&
					    info->data[7] == 0x10 && info->data[8] == 0x16 && info->data[9] == 0xAA && info->data[10] == 0xFE &&
					    info->data[11] == 0x21 && info->data[12] == 0x00) {
					    printf("%s %d", addr, (int8_t)info->data[info->length]);
					    for (int i = 0; i < info->length; i++)
						printf(" %02X", (unsigned char)info->data[i]);
					    	printf("\n");
					    	process_data(info);
					}
				    }
				    offset = info->data + info->length + 2;
				}
			}
		}
	}

	// Prevent SIGALARM from firing during the clean up procedure
	if ( sigprocmask( SIG_BLOCK, &sigalrm_set, NULL ) != 0 )
	{
		hci_close_dev(device);
		perror( "Could not block alarm signal" );
		return 0;
	}

	exit_clean();
	return 0;
}



